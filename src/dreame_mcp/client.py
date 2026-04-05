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
import logging
import os
import sys
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
MAP_FETCH_TIMEOUT = 45  # map can be slow — higher ceiling
CONNECT_TIMEOUT = 30  # login + MQTT setup

# ---------------------------------------------------------------------------
# Tasshack ref clone bootstrap
# ---------------------------------------------------------------------------

_REF_DEFAULT = Path("D:/Dev/repos/tasshack_dreame_vacuum_ref")
_DREAME_PKG = "custom_components.dreame_vacuum.dreame"

_protocol_cls = None   # DreameVacuumDreameHomeCloudProtocol
_map_manager_cls = None  # DreameVacuumMapManager (optional, heavy)


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
    global _protocol_cls, _map_manager_cls

    if _protocol_cls is not None:
        return  # already loaded

    dreame_dir = ref_path / "custom_components" / "dreame_vacuum" / "dreame"
    if not dreame_dir.exists():
        raise RuntimeError(f"Tasshack ref clone not found at: {dreame_dir}")

    _stub_miio()
    _stub_ha()

    # Parent stubs so relative imports in protocol.py work
    for pkg in ["custom_components",
                "custom_components.dreame_vacuum",
                _DREAME_PKG]:
        if pkg not in sys.modules:
            sys.modules[pkg] = _types.ModuleType(pkg)

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
        logger.info("Tasshack map module loaded OK (map rendering available)")
    except Exception as e:
        logger.warning("Tasshack map module load failed — map rendering unavailable: %s", e)
        _map_manager_cls = None

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
        if not self._protocol:
            return {"success": False, "error": "Not connected"}
        try:
            # Get the object_name from the protocol's computed property.
            # NOTE: Previously tried get_properties(["6.3"]) for live lookup,
            # but the Tasshack API response shape doesn't match simple dict key
            # lookup. The computed object_name (model/uid/did/0) is the reliable path.
            object_name = getattr(self._protocol, "object_name", None)

            if not object_name or not str(object_name).strip("/"):
                return {
                    "success": False,
                    "error": "object_name unavailable (map not published yet or cloud property lookup failed)",
                }

            object_name = str(object_name).strip()
            logger.info("Map fetch: object_name=%s", object_name)

            # Fetch raw map file from cloud.
            # Different firmwares/backends require different `type` values.
            # Fail fast: stop after first cloud error (not timeout) to avoid
            # cumulative 60s+ blocking on 4 variants.
            raw = None
            attempted: list[dict[str, str]] = []
            fail_count = 0
            max_fails = 2  # bail after 2 cloud failures — don't try all 4

            for file_type in ("map", 0, "0", object_name):
                if fail_count >= max_fails:
                    logger.warning("Map fetch: %d cloud failures, skipping remaining type variants", fail_count)
                    break
                try:
                    attempted.append({"filename": object_name, "type": str(file_type)})
                    logger.debug("Map fetch: trying type=%s", file_type)
                    raw = self._protocol.get_device_file(object_name, file_type)
                except Exception as e:
                    logger.warning("Map fetch type=%s failed: %s", file_type, e)
                    raw = None
                    fail_count += 1
                if raw is not None:
                    logger.info("Map fetch: success with type=%s (%d bytes)", file_type, len(raw))
                    break

            # Signed URL fallback (some backends don't allow direct file fetch)
            if raw is None:
                try:
                    obj_for_url = object_name if object_name.startswith("/") else f"/{object_name}"
                    url_data = self._protocol.get_file_url(obj_for_url)
                    url = None
                    if isinstance(url_data, dict):
                        url = url_data.get("url") or url_data.get("fileUrl")
                    if isinstance(url, str) and url.strip():
                        attempted.append({"filename": obj_for_url, "type": "signed_url"})
                        logger.info("Map fetch: trying signed URL")
                        raw = self._protocol.get_file(url.strip())
                except Exception as e:
                    logger.warning("Map fetch signed URL failed: %s", e)
                    raw = None

            if raw is None:
                return {
                    "success": False,
                    "error": "Map fetch failed (cloud returned no file data)",
                    "diagnostic_info": {
                        "did": str(self._did),
                        "country": getattr(self._protocol, "_country", None),
                        "object_name": object_name,
                        "attempted": attempted,
                        "hint": "If this persists, ensure the robot has created a map, and that DREAME_COUNTRY/DREAME_DID are correct.",
                    },
                }

            result: dict[str, Any] = {
                "success": True,
                "object_name": object_name,
                "raw_bytes": len(raw),
            }

            # Decode + render via map manager if available
            if self._map_manager is not None:
                try:
                    map_data = self._map_manager.decode_map(raw)
                    if map_data:
                        image = self._map_manager.render_map(map_data)
                        if image:
                            import io
                            buf = io.BytesIO()
                            image.save(buf, format="PNG")
                            result["image"] = base64.b64encode(buf.getvalue()).decode()
                            result["map_data"] = {
                                "rooms": len(getattr(map_data, "segments", {}) or {}),
                                "robot_position": _point_to_dict(getattr(map_data, "robot_position", None)),
                                "charger_position": _point_to_dict(getattr(map_data, "charger_position", None)),
                            }
                except Exception as e:
                    logger.warning("Map decode/render failed: %s", e)
                    result["render_error"] = str(e)

            # Always return raw as base64 fallback
            result["raw_b64"] = base64.b64encode(raw).decode()
            return result

        except Exception as e:
            logger.exception("get_map failed")
            return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
