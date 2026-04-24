"""DreameHome cloud client wrapping Tasshack dreame-vacuum protocol + map layers.

Loads protocol.py and map.py from the ref clone at DREAME_REF_PATH (or auto-detected
sibling directory tasshack_dreame_vacuum_ref). Stubs out miio/HA imports so the
Tasshack code loads without a full HA installation.

Env vars:
    DREAME_USER         DreameHome email/phone
    DREAME_PASSWORD     DreameHome password
    DREAME_COUNTRY      Cloud region, default: eu
    DREAME_DID          Device ID (optional, auto-selected if single device)
    DREAME_AUTH_KEY     Refresh token from previous login (optional, speeds up startup)
    DREAME_REF_PATH     Path to tasshack_dreame_vacuum_ref clone
                        (default: sibling of this repo at D:/Dev/repos/tasshack_dreame_vacuum_ref)
"""
from __future__ import annotations

import asyncio
import base64
import importlib.util
import json
import logging
import os
import sys
import threading
import types as _types
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("dreame-mcp.client")

# ---------------------------------------------------------------------------
# Timeouts (seconds)
# ---------------------------------------------------------------------------

EXECUTOR_TIMEOUT = 35  # max wall-clock for any run_in_executor call
MAP_FETCH_TIMEOUT = 60  # URL + optional get_device_file fallback; avoid racing the asyncio guard
CONNECT_TIMEOUT = 30  # login + MQTT setup

# ---------------------------------------------------------------------------
# Tasshack ref clone bootstrap
# ---------------------------------------------------------------------------

_REF_DEFAULT = Path("D:/Dev/repos/tasshack_dreame_vacuum_ref")
_DREAME_PKG = "custom_components.dreame_vacuum.dreame"

_protocol_cls = None   # DreameVacuumDreameHomeCloudProtocol
_map_manager_cls = None  # DreameMapVacuumMapManager (optional, heavy)
_map_decoder_cls = None  # DreameVacuumMapDecoder (static decode_map on map.py)
_map_renderer_cls = None  # DreameVacuumMapRenderer (render_map → bytes)


def _stub_miio():
    """Stub out miio so protocol.py loads without it."""
    if "miio" in sys.modules:
        return
    miio_mod = _types.ModuleType("miio")
    proto_mod = _types.ModuleType("miio.miioprotocol")

    class _MiIOProtocol:
        def __init__(self, *a, **kw):
            pass

    proto_mod.MiIOProtocol = _MiIOProtocol
    sys.modules["miio"] = miio_mod
    sys.modules["miio.miioprotocol"] = proto_mod


def _stub_ha():
    """Stub homeassistant package so nothing in the chain blows up."""
    for mod in ["homeassistant", "homeassistant.core", "homeassistant.helpers",
                "homeassistant.helpers.entity", "homeassistant.components"]:
        if mod not in sys.modules:
            sys.modules[mod] = _types.ModuleType(mod)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _bootstrap_tasshack(ref_path: Path):
    """Load protocol + map from the ref clone. Idempotent."""
    global _protocol_cls, _map_manager_cls, _map_decoder_cls, _map_renderer_cls

    if _protocol_cls is not None:
        return  # already loaded

    cc_dir = ref_path / "custom_components"
    dv_dir = cc_dir / "dreame_vacuum"
    dreame_dir = dv_dir / "dreame"
    if not dreame_dir.exists():
        raise RuntimeError(f"Tasshack ref clone not found at: {dreame_dir}")

    _stub_miio()
    _stub_ha()

    # Package stubs with __path__ so submodules (e.g. .types) resolve — a bare
    # ModuleType without __path__ is "not a package" and map.py fails to import.
    for name, p in [
        ("custom_components", cc_dir),
        ("custom_components.dreame_vacuum", dv_dir),
        (_DREAME_PKG, dreame_dir),
    ]:
        m = sys.modules.get(name) or _types.ModuleType(name)
        m.__path__ = [str(p)]
        sys.modules[name] = m

    # Load exceptions (no deps)
    exc_mod = _load_module(f"{_DREAME_PKG}.exceptions", dreame_dir / "exceptions.py")

    # Inject VERSION into the dreame package stub
    dreame_stub = sys.modules[_DREAME_PKG]
    dreame_stub.VERSION = "dreame-mcp-adapter"
    dreame_stub.DeviceException = exc_mod.DeviceException
    dreame_stub.DeviceUpdateFailedException = exc_mod.DeviceUpdateFailedException

    # Load protocol (needs exceptions stub above)
    proto_mod = _load_module(f"{_DREAME_PKG}.protocol", dreame_dir / "protocol.py")
    _protocol_cls = proto_mod.DreameVacuumDreameHomeCloudProtocol

    # Load map — heavy, best-effort. Many deps (py_mini_racer, numpy, PIL…)
    # We try; if it fails we log a warning and map rendering will be unavailable.
    try:
        # map.py imports from .types, .resources, .protocol — load them first
        _load_module(f"{_DREAME_PKG}.const", dreame_dir / "const.py")
        _load_module(f"{_DREAME_PKG}.types", dreame_dir / "types.py")
        _load_module(f"{_DREAME_PKG}.resources", dreame_dir / "resources.py")
        map_mod = _load_module(f"{_DREAME_PKG}.map", dreame_dir / "map.py")
        # NOTE: upstream class name is DreameMapVacuumMapManager (not DreameVacuumMapManager).
        _map_manager_cls = (
            getattr(map_mod, "DreameMapVacuumMapManager", None)
            or getattr(map_mod, "DreameVacuumMapManager", None)
        )
        _map_decoder_cls = getattr(map_mod, "DreameVacuumMapDecoder", None)
        _map_renderer_cls = getattr(map_mod, "DreameVacuumMapRenderer", None)
        logger.info("Tasshack map module loaded OK (map rendering available)")
    except Exception as e:
        logger.warning("Tasshack map module load failed — map rendering unavailable: %s", e)
        _map_manager_cls = None
        _map_decoder_cls = None
        _map_renderer_cls = None

    logger.info("Tasshack protocol loaded from %s", ref_path)


# ---------------------------------------------------------------------------
# Status dataclass
# ---------------------------------------------------------------------------

@dataclass
class DreameStatus:
    state: str = "unknown"
    battery: int = 0
    fan_speed: str = "unknown"
    is_charging: bool = False
    is_cleaning: bool = False
    cleaned_area: float = 0.0
    cleaning_time: int = 0
    error: str | None = None
    raw: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# MiIO property IDs for basic status
# ref: custom_components/dreame_vacuum/dreame/types.py  PIID
# ---------------------------------------------------------------------------

_PROP_STATE    = {"did": None, "siid": 2, "piid": 1}   # operating state enum
_PROP_ERROR    = {"did": None, "siid": 2, "piid": 2}   # error code
_PROP_BATTERY  = {"did": None, "siid": 3, "piid": 1}   # battery %
_PROP_CHARGING = {"did": None, "siid": 3, "piid": 2}   # charging status
_PROP_STATUS   = {"did": None, "siid": 4, "piid": 1}   # detailed status
_PROP_TIME     = {"did": None, "siid": 4, "piid": 2}   # cleaning time s
_PROP_AREA     = {"did": None, "siid": 4, "piid": 3}   # cleaned area cm²
_PROP_FANSPEED = {"did": None, "siid": 4, "piid": 4}   # suction level

_STATE_MAP = {
    0: "idle", 1: "cleaning", 2: "returning", 3: "charging",
    4: "charging_error", 5: "paused", 6: "sweeping_and_mopping",
    7: "mopping", 8: "drying", 9: "self_cleaning",
    10: "remote_control", 11: "fast_mapping", 12: "pending",
    17: "docked",
}

_ACTION_MAP = {
    # siid/aiid from Tasshack DreameVacuumActionMapping (types.py)
    "start_clean": (2, 1),   # START
    "pause":       (2, 2),   # PAUSE
    "go_home":     (3, 1),   # CHARGE — was wrong (2,4), correct is siid:3 aiid:1
    "stop":        (4, 2),   # STOP
    "find_robot":  (7, 1),   # LOCATE
}


# ---------------------------------------------------------------------------
# DreameHomeClient
# ---------------------------------------------------------------------------

class DreameHomeClient:
    """Async-friendly wrapper around DreameVacuumDreameHomeCloudProtocol.

    All public async methods are guarded with asyncio.wait_for() to prevent
    indefinite hangs when the DreameHome cloud is unreachable or slow.
    """

    def __init__(
        self,
        username: str,
        password: str,
        country: str = "eu",
        did: str | None = None,
        auth_key: str | None = None,
        ref_path: Path | None = None,
    ):
        self._username = username
        self._password = password
        self._country = country
        self._did = did
        self._auth_key = auth_key
        self._ref_path = ref_path or _REF_DEFAULT
        self._protocol = None
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="dreame")
        self._map_manager = None
        self._map_renderer = None
        # Serialize map downloads — dashboard + Status poll can overlap and starve the pool / hit 45s+ timeouts
        self._map_fetch_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """Bootstrap Tasshack libs, login, discover device. Timeout-guarded."""
        loop = asyncio.get_event_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(self._executor, self._connect_sync),
                timeout=CONNECT_TIMEOUT,
            )
        except TimeoutError:
            logger.error("connect() timed out after %ds", CONNECT_TIMEOUT)
            return False

    def _connect_sync(self) -> bool:
        try:
            _bootstrap_tasshack(self._ref_path)
        except Exception as e:
            logger.error("Bootstrap failed: %s", e)
            return False

        self._protocol = _protocol_cls(
            username=self._username,
            password=self._password,
            country=self._country,
            account_type="dreame",
            auth_key=self._auth_key,
            did=str(self._did) if self._did else None,
        )

        ok = self._protocol.login()
        if not ok:
            logger.error("DreameHome login failed")
            return False
        logger.info("DreameHome login OK, auth_key=%s…", (self._protocol.auth_key or "")[:20])

        # Auto-discover DID if not provided
        if not self._did:
            devices = self._protocol.get_devices()
            if not devices:
                logger.error("No devices returned from cloud")
                return False
            records = devices.get("page", {}).get("records", [])
            if not records:
                logger.error("Device list empty")
                return False
            device = records[0]
            self._did = str(device.get("did", ""))
            name = device.get("customName") or device.get("deviceInfo", {}).get("displayName", "?")
            logger.info("Auto-selected device: %s (DID=%s)", name, self._did)
            self._protocol._did = self._did

        # Connect MQTT for push updates (non-fatal if it fails)
        try:
            info = self._protocol.connect()
            if info:
                logger.info("MQTT connected, host=%s", self._protocol._host)
        except Exception as e:
            logger.warning("MQTT connect failed (polling will still work): %s", e)

        # Init map manager if available
        if _map_manager_cls is not None:
            try:
                self._map_manager = _map_manager_cls(self._protocol)
                logger.info("Map manager initialized")
            except Exception as e:
                logger.warning("Map manager init failed: %s", e)
        if _map_renderer_cls is not None and self._map_renderer is None:
            try:
                # low_resolution: faster, less memory (same flags as many HA configs)
                self._map_renderer = _map_renderer_cls(low_resolution=True, cache=True)
            except Exception as e:
                logger.warning("DreameVacuumMapRenderer init failed: %s", e)

        return True

    def disconnect(self):
        if self._protocol:
            try:
                self._protocol.disconnect()
            except Exception:
                pass
        self._executor.shutdown(wait=False)

    @property
    def connected(self) -> bool:
        return self._protocol is not None and self._protocol.logged_in

    @property
    def auth_key(self) -> str | None:
        return self._protocol.auth_key if self._protocol else None

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    async def get_status(self) -> DreameStatus:
        """Fetch robot status. Timeout-guarded."""
        loop = asyncio.get_event_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(self._executor, self._get_status_sync),
                timeout=EXECUTOR_TIMEOUT,
            )
        except TimeoutError:
            logger.error("get_status() timed out after %ds", EXECUTOR_TIMEOUT)
            return DreameStatus(error=f"Status request timed out ({EXECUTOR_TIMEOUT}s)")

    def _get_status_sync(self) -> DreameStatus:
        if not self._protocol:
            return DreameStatus(error="Not connected")
        try:
            did = str(self._did)
            props = [
                {**_PROP_STATE,    "did": did},
                {**_PROP_ERROR,    "did": did},
                {**_PROP_BATTERY,  "did": did},
                {**_PROP_CHARGING, "did": did},
                {**_PROP_STATUS,   "did": did},
                {**_PROP_TIME,     "did": did},
                {**_PROP_AREA,     "did": did},
                {**_PROP_FANSPEED, "did": did},
            ]
            result = self._protocol.send("get_properties", props)
            if result is None:
                return DreameStatus(error="No response from device")

            raw = {f"{r['siid']}.{r['piid']}": r.get("value") for r in result if "value" in r}

            state_code    = raw.get("2.1", 0)    # STATE
            battery       = raw.get("3.1", 0)    # BATTERY_LEVEL
            charging_code = raw.get("3.2", 0)    # CHARGING_STATUS
            fan_speed     = raw.get("4.4", 0)    # SUCTION_LEVEL
            time_s        = raw.get("4.2", 0) or 0  # CLEANING_TIME
            area_cm2      = raw.get("4.3", 0) or 0  # CLEANED_AREA

            state_str  = _STATE_MAP.get(state_code, f"state_{state_code}")
            is_charging = charging_code in (1, 2)
            is_cleaning = state_code in (1, 6, 7, 11)

            return DreameStatus(
                state=state_str,
                battery=int(battery),
                fan_speed=str(fan_speed),
                is_charging=is_charging,
                is_cleaning=is_cleaning,
                cleaned_area=round(area_cm2 / 10000, 2),
                cleaning_time=int(time_s),
                raw=raw,
            )
        except Exception as e:
            logger.exception("get_status failed")
            return DreameStatus(error=str(e))

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------

    async def control(self, cmd: str) -> dict:
        """Send control command. Timeout-guarded."""
        loop = asyncio.get_event_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(self._executor, self._control_sync, cmd),
                timeout=EXECUTOR_TIMEOUT,
            )
        except TimeoutError:
            logger.error("control(%s) timed out after %ds", cmd, EXECUTOR_TIMEOUT)
            return {"success": False, "error": f"Control request timed out ({EXECUTOR_TIMEOUT}s)"}

    def _control_sync(self, cmd: str) -> dict:
        if not self._protocol:
            return {"success": False, "error": "Not connected"}
        if cmd not in _ACTION_MAP:
            return {"success": False, "error": f"Unknown command: {cmd}"}
        try:
            siid, aiid = _ACTION_MAP[cmd]
            result = self._protocol.send(
                "action",
                {"did": str(self._did), "siid": siid, "aiid": aiid, "in": []},
            )
            if result is not None:
                return {"success": True, "message": f"Sent {cmd}", "result": result}
            return {"success": False, "error": f"No response for {cmd}"}
        except Exception as e:
            logger.exception("control(%s) failed", cmd)
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Map — the critical path that was hanging
    # ------------------------------------------------------------------

    def _resolve_live_map_object_name(self) -> str | None:
        """HA map.py: prefer OBJECT_NAME from get_properties(6.3) over the model/uid/did/0 string alone."""
        proto = self._protocol
        if proto is None:
            return None
        if getattr(proto, "dreame_cloud", True):
            try:
                from custom_components.dreame_vacuum.dreame.const import MAP_PARAMETER_VALUE
                from custom_components.dreame_vacuum.dreame.types import DIID, DreameVacuumProperty

                r = proto.get_properties(DIID(DreameVacuumProperty.OBJECT_NAME))
                if r and len(r) > 0:
                    first = r[0]
                    val = first.get(MAP_PARAMETER_VALUE) or first.get("value")
                    if val is not None:
                        if isinstance(val, (list, tuple)) and val:
                            return str(val[0])
                        if isinstance(val, str):
                            s = val.strip()
                            if s.startswith("["):
                                j = json.loads(s)
                                if isinstance(j, (list, tuple)) and j:
                                    return str(j[0])
                            return s
            except Exception as e:
                logger.debug("get_properties(OBJECT_NAME): %s", e)
        on = getattr(proto, "object_name", None)
        if on:
            return str(on).strip()
        return None

    def _fetch_map_bytes_from_cloud_url(self, object_name: str) -> bytes | None:
        """Same order as Tasshack map._get_interim_file_data: interim URL, then get_file; not get_device_file."""
        proto = self._protocol
        u: Any = None
        try:
            u = proto.get_interim_file_url(object_name)  # type: ignore[union-attr]
        except Exception as e:
            logger.debug("get_interim_file_url: %s", e)
        if u is not None and not (isinstance(u, str) and (u or "").strip().lower().startswith("http")):
            if isinstance(u, dict):
                u2 = (u or {}).get("url") or (u or {}).get("fileUrl")
                u = u2 if isinstance(u2, str) else None
            else:
                u = None
        if not u and hasattr(proto, "get_file_url"):
            o = object_name if str(object_name).startswith("/") else f"/{object_name}"
            try:
                d = proto.get_file_url(o)
            except Exception as e:
                logger.debug("get_file_url: %s", e)
                d = None
            if isinstance(d, dict):
                u = d.get("url") or d.get("fileUrl")
            elif isinstance(d, str) and d.strip().lower().startswith("http"):
                u = d
        if not u or not str(u).strip().lower().startswith("http"):
            return None
        try:
            raw = proto.get_file(str(u).strip())
        except Exception as e:
            logger.warning("get_file(signed URL) failed: %s", e)
            return None
        if not raw or _map_bytes_looks_like_error_json(raw):
            return None
        return raw

    async def get_map(self) -> dict:
        """Fetch and decode the current map. Returns base64 PNG if rendering works.

        Timeout-guarded: aborts after MAP_FETCH_TIMEOUT seconds to prevent
        indefinite hangs when DreameHome cloud is unreachable.
        """
        loop = asyncio.get_event_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(self._executor, self._get_map_sync),
                timeout=MAP_FETCH_TIMEOUT,
            )
        except TimeoutError:
            logger.error("get_map() timed out after %ds", MAP_FETCH_TIMEOUT)
            return {
                "success": False,
                "error": f"Map request timed out ({MAP_FETCH_TIMEOUT}s). "
                         "DreameHome cloud may be unreachable.",
                "timeout": True,
            }

    def _get_map_sync(self) -> dict:
        with self._map_fetch_lock:
            if not self._protocol:
                return {"success": False, "error": "Not connected"}
            try:
                object_name = self._resolve_live_map_object_name()
                if not object_name or not str(object_name).strip("/"):
                    return {
                        "success": False,
                        "error": "object_name unavailable (map not published yet or cloud property lookup failed)",
                    }
                object_name = str(object_name).strip()
                logger.info("Map fetch: object_name=%s (signed-URL first; get_device_file fallback)", object_name)
                attempted: list[dict[str, str]] = []
                raw: bytes | None = self._fetch_map_bytes_from_cloud_url(object_name)
                if raw:
                    logger.info("Map fetch: %d bytes via get_interim_file_url / get_file (Home Assistant path)", len(raw))
                    attempted.append({"step": "get_interim_file_url+get_file", "object_name": object_name})
                for file_type in ("map", 0):
                    if raw is not None:
                        break
                    step = f"get_device_file:{file_type!s}"
                    attempted.append({"step": step, "object_name": object_name})
                    try:
                        chunk = self._protocol.get_device_file(object_name, file_type)
                    except Exception as e:
                        logger.warning("Map %s: %s", step, e)
                        continue
                    if chunk is not None and not _map_bytes_looks_like_error_json(chunk):
                        raw = chunk
                        logger.info("Map fetch: %s -> %d bytes", step, len(raw))
                        break

                if raw is None or _map_bytes_looks_like_error_json(raw):
                    return {
                        "success": False,
                        "error": "Map fetch failed (signed URL and device file both failed)",
                        "diagnostic_info": {
                            "did": str(self._did),
                            "country": getattr(self._protocol, "_country", None),
                            "object_name": object_name,
                            "attempted": attempted,
                            "hint": "get_device_file often returns 80001 (cloud cannot reach the vac). This path uses a signed-URL download first, like Home Assistant. Wake the robot, open the Dreame app on the same account, then retry; confirm DREAME_COUNTRY and DREAME_DID match the app.",
                        },
                    }

                result: dict[str, Any] = {
                    "success": True,
                    "object_name": object_name,
                    "raw_bytes": len(raw),
                }

                if _map_decoder_cls and self._map_renderer:
                    try:
                        # Map manager is not a decoder: use DreameVacuumMapDecoder + DreameVacuumMapRenderer
                        # (Home Assistant map camera), not manager.decode_map.
                        raw_str = _map_raw_bytes_to_str(raw)
                        mm = self._map_manager
                        vslam = bool(getattr(mm, "_vslam_map", False)) if mm is not None else False
                        aes_iv = getattr(mm, "_aes_iv", None) if mm is not None else None
                        decoded = _map_decoder_cls.decode_map(raw_str, vslam, 0, aes_iv, None)
                        map_data = None
                        if isinstance(decoded, tuple) and len(decoded) > 0:
                            map_data = decoded[0]
                        elif decoded is not None:
                            map_data = decoded
                        if map_data is not None:
                            out = self._map_renderer.render_map(map_data, 0, 0)
                            if out:
                                result["image"] = base64.b64encode(out).decode()
                                result["map_data"] = {
                                    "rooms": len(getattr(map_data, "segments", {}) or {}),
                                    "robot_position": _point_to_dict(getattr(map_data, "robot_position", None)),
                                    "charger_position": _point_to_dict(getattr(map_data, "charger_position", None)),
                                }
                        else:
                            result["render_error"] = "decode_map returned no MapData (partial decode failed or wrong key)"
                    except Exception as e:
                        logger.warning("Map decode/render failed: %s", e)
                        result["render_error"] = str(e)
                else:
                    missing: list[str] = []
                    if not _map_decoder_cls or not _map_renderer_cls:
                        missing.append("Tasshack map import")
                    if self._map_renderer is None and _map_renderer_cls:
                        missing.append("renderer init")
                    result["render_error"] = "Map PNG unavailable: " + (", ".join(missing) or "unknown")

                result["raw_b64"] = base64.b64encode(raw).decode()
                return result

            except Exception as e:
                logger.exception("get_map failed")
                return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _map_raw_bytes_to_str(raw: bytes) -> str:
    """Tasshack `decode_map` expects a str; cloud files are typically UTF-8 or Latin-1–safe text."""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def _map_bytes_looks_like_error_json(raw: bytes | None) -> bool:
    """True if cloud returned a JSON error body instead of a map blob (HTTP 200+error is possible)."""
    if not raw or len(raw) < 2 or raw[0:1] != b"{":
        return False
    try:
        j = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False
    if not isinstance(j, dict):
        return False
    if j.get("success") is False:
        return True
    c = j.get("code")
    if c is not None and c not in (0, "0"):
        return True
    return False


def _point_to_dict(point) -> dict | None:
    if point is None:
        return None
    return {"x": getattr(point, "x", None), "y": getattr(point, "y", None)}


def client_from_env() -> DreameHomeClient | None:
    """Build a DreameHomeClient from environment variables."""
    user = os.environ.get("DREAME_USER", "").strip()
    pwd  = os.environ.get("DREAME_PASSWORD", "").strip()
    if not user or not pwd:
        logger.warning("DREAME_USER and DREAME_PASSWORD not set — running in stub mode")
        return None

    ref_raw = os.environ.get("DREAME_REF_PATH", "").strip()
    ref_path = Path(ref_raw) if ref_raw else _REF_DEFAULT

    return DreameHomeClient(
        username=user,
        password=pwd,
        country=os.environ.get("DREAME_COUNTRY", "eu").strip(),
        did=os.environ.get("DREAME_DID", "").strip() or None,
        auth_key=os.environ.get("DREAME_AUTH_KEY", "").strip() or None,
        ref_path=ref_path,
    )
