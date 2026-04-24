"""DreameHome cloud client wrapping Tasshack dreame-vacuum protocol + map layers.

Loads protocol.py and map.py from the ref clone at DREAME_REF_PATH (or auto-detected
sibling directory tasshack_dreame_vacuum_ref). Stubs out miio/HA imports so the
Tasshack code loads without a full HA installation.

Env vars:
    DREAME_USER         DreameHome email/phone
    DREAME_PASSWORD     DreameHome password
    DREAME_COUNTRY      Cloud region, default: eu
    DREAME_IP           Lokal IP address for MiIO (circumvention method)
    DREAME_TOKEN        Lokal MiIO token
    DREAME_DID          Device ID (optional, auto-selected if single device)
    DREAME_AUTH_KEY     Refresh token from previous login (optional, speeds up startup)
    DREAME_REF_PATH     Path to Tasshack/dreame-vacuum clone
                        (default: D:/Dev/repos/tasshack_dreame_vacuum_ref)
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

from dotenv import load_dotenv

logger = logging.getLogger("dreame-mcp.client")

# ---------------------------------------------------------------------------
# Timeouts (seconds)
# ---------------------------------------------------------------------------

EXECUTOR_TIMEOUT = 35  # max wall-clock for any run_in_executor call
MAP_FETCH_TIMEOUT = 60  # signed URL + decode/render; align with tests and slow cloud
CONNECT_TIMEOUT = 30  # login + MQTT setup

# ---------------------------------------------------------------------------
# Tasshack ref clone bootstrap
# ---------------------------------------------------------------------------

_REF_DEFAULT = Path("D:/Dev/repos/tasshack_dreame_vacuum_ref")
_DREAME_PKG = "custom_components.dreame_vacuum.dreame"

_protocol_cls = None  # DreameVacuumProtocol (Local + Cloud)
_map_manager_cls = None  # DreameMapVacuumMapManager (optional, heavy)
_map_decoder_cls = None  # DreameVacuumMapDecoder (static decode_map on map.py)
_map_renderer_cls = None  # DreameVacuumMapRenderer (render_map → bytes)


def _stub_miio():
    """Stub out miio only if not installed, avoiding AttributeError on .send() if real miio is available."""
    if importlib.util.find_spec("miio"):
        return

    if "miio" in sys.modules:
        return

    logger.warning("python-miio not found â€” using stubs (local control will fail)")
    miio_mod = _types.ModuleType("miio")
    proto_mod = _types.ModuleType("miio.miioprotocol")

    class _MiIOProtocol:
        def __init__(self, *a, **kw):
            pass

        def send(self, *a, **kw):
            raise RuntimeError("miio.send() called on a stub. Local control requires python-miio.")

    proto_mod.MiIOProtocol = _MiIOProtocol
    sys.modules["miio"] = miio_mod
    sys.modules["miio.miioprotocol"] = proto_mod


def _stub_ha():
    """Stub homeassistant package so nothing in the chain blows up."""
    for mod in [
        "homeassistant",
        "homeassistant.core",
        "homeassistant.helpers",
        "homeassistant.helpers.entity",
        "homeassistant.components",
    ]:
        if mod not in sys.modules:
            sys.modules[mod] = _types.ModuleType(mod)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _bootstrap_protocol(ref_path: Path):
    """Load unified protocol + map from the external reference repo. Idempotent."""
    global _protocol_cls, _map_manager_cls, _map_decoder_cls, _map_renderer_cls

    if _protocol_cls is not None:
        return

    cc_dir = ref_path / "custom_components"
    dv_dir = cc_dir / "dreame_vacuum"
    dreame_dir = dv_dir / "dreame"
    if not dreame_dir.exists():
        raise RuntimeError(f"External protocol reference not found at: {dreame_dir}")

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

    # Load types and exceptions first
    _load_module(f"{_DREAME_PKG}.exceptions", dreame_dir / "exceptions.py")
    _load_module(f"{_DREAME_PKG}.types", dreame_dir / "types.py")
    _load_module(f"{_DREAME_PKG}.const", dreame_dir / "const.py")

    # Inject constants into package stub
    dreame_stub = sys.modules[_DREAME_PKG]
    dreame_stub.DeviceException = sys.modules[f"{_DREAME_PKG}.exceptions"].DeviceException
    dreame_stub.VERSION = "dreame-mcp-adapter"

    # Load protocol (unified local/cloud)
    proto_mod = _load_module(f"{_DREAME_PKG}.protocol", dreame_dir / "protocol.py")
    _protocol_cls = proto_mod.DreameVacuumProtocol

    # Load map
    try:
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
        logger.warning("Map module load failed: %s", e)
        _map_manager_cls = None
        _map_decoder_cls = None
        _map_renderer_cls = None

    logger.info("Protocol loaded from %s", ref_path)


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

_PROP_STATE = {"did": None, "siid": 2, "piid": 1}  # operating state enum
_PROP_ERROR = {"did": None, "siid": 2, "piid": 2}  # error code
_PROP_BATTERY = {"did": None, "siid": 3, "piid": 1}  # battery %
_PROP_CHARGING = {"did": None, "siid": 3, "piid": 2}  # charging status
_PROP_STATUS = {"did": None, "siid": 4, "piid": 1}  # detailed status
_PROP_TIME = {"did": None, "siid": 4, "piid": 2}  # cleaning time s
_PROP_AREA = {"did": None, "siid": 4, "piid": 3}  # cleaned area cmÂ²
_PROP_FANSPEED = {"did": None, "siid": 4, "piid": 4}  # suction level

# ref: custom_components/dreame_vacuum/dreame/types.py  DreameVacuumState
_STATE_MAP = {
    1: "sweeping",
    2: "idle",
    3: "paused",
    4: "error",
    5: "returning",
    6: "charging",
    7: "mopping",
    8: "drying",
    9: "washing",
    10: "returning_washing",
    11: "building",
    12: "sweeping_and_mopping",
    13: "charging_completed",
    14: "upgrading",
}

_ACTION_MAP = {
    # ref: custom_components/dreame_vacuum/dreame/types.py  DreameVacuumActionMapping
    "start_clean": (2, 1),  # START
    "pause": (2, 2),  # PAUSE
    "go_home": (3, 1),  # CHARGE
    "stop": (4, 2),  # STOP
    "find_robot": (7, 1),  # LOCATE
}


def _pick_cloud_device(devices: list, want_ip: str | None) -> dict | None:
    """Select one device from get_devices() for map/DID. Avoid wrong-robot `devices[0]`."""
    if not devices:
        return None
    if want_ip:
        m = next((d for d in devices if d.get("localip") == want_ip), None)
        if m:
            return m
    if len(devices) == 1:
        d0 = devices[0]
        lip = d0.get("localip")
        if want_ip and lip and str(lip) not in ("", "Unknown", "unknown") and lip != want_ip:
            logger.warning(
                "Only one cloud device: localip=%r != DREAME_IP=%r — set DREAME_DID if this is the wrong device.",
                lip,
                want_ip,
            )
        return d0
    if want_ip:
        logger.error(
            "DREAME_IP not in cloud list (stale Dreame app data). Set DREAME_DID. Reported localips: %s",
            [d.get("localip") for d in devices],
        )
    else:
        logger.error("Multiple cloud devices: set DREAME_DID or DREAME_IP to pick the right vacuum.")
    return None


def _miot_did_slots(n: int, cloud_did: str | None) -> list[str]:
    """Miot get_properties `did` is a per-request slot / correlation id (Tasshack uses property enum).

    The cloud numeric device id is only one valid pattern. When it is missing, use "0".."n-1"
    (never the string "None" — that breaks local miio).
    """
    if cloud_did:
        s = str(cloud_did).strip()
        if s and s.lower() != "none":
            return [s] * n
    return [str(i) for i in range(n)]


# ---------------------------------------------------------------------------
# DreameHomeClient
# ---------------------------------------------------------------------------


class DreameHomeClient:
    """Async-friendly wrapper around DreameVacuumProtocol (Hybrid Local/Cloud)."""

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        country: str = "eu",
        ip: str | None = None,
        token: str | None = None,
        did: str | None = None,
        auth_key: str | None = None,
        ref_path: Path | None = None,
    ):
        self._username = username
        self._password = password
        self._country = country
        self._ip = ip
        self._token = token if token else "0" * 32
        self._did = did
        self._auth_key = auth_key
        self._ref_path = ref_path or _REF_DEFAULT
        self._protocol = None
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="dreame")
        self._map_manager = None
        self._map_renderer = None
        # Serialize map downloads (dashboard + status poll can overlap the executor).
        self._map_fetch_lock = threading.Lock()
        # Last exception from a failed protocol call (e.g. miio) for clearer API errors.
        self._last_protocol_error: str | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """Bootstrap Tasshack protocol with null token trick for local control.

        - DREAME_IP set, DREAME_TOKEN blank -> null token ("0"*32) passed to protocol
        - The Tasshack DreameVacuumProtocol handles the null-token local path internally
        - Cloud login attempted only if USER+PASSWORD present (for maps only)
        - No MiotDevice, no cloud token extraction (DreameHome does not provide tokens)
        """
        loop = asyncio.get_event_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(self._executor, self._connect_sync),
                timeout=CONNECT_TIMEOUT,
            )
        except TimeoutError:
            logger.error("connect() timed out after %ds", CONNECT_TIMEOUT)
            return False

    async def get_status(self) -> DreameStatus:
        """Fetch robot status via Tasshack protocol. Timeout-guarded."""
        loop = asyncio.get_event_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(self._executor, self._get_status_sync),
                timeout=EXECUTOR_TIMEOUT,
            )
        except TimeoutError:
            logger.error("get_status() timed out after %ds", EXECUTOR_TIMEOUT)
            return DreameStatus(error=f"Status request timed out ({EXECUTOR_TIMEOUT}s)")

    async def control(self, cmd: str) -> dict:
        """Send control command via Tasshack protocol. Timeout-guarded."""
        loop = asyncio.get_event_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(self._executor, self._control_sync, cmd),
                timeout=EXECUTOR_TIMEOUT,
            )
        except TimeoutError:
            logger.error("control(%s) timed out after %ds", cmd, EXECUTOR_TIMEOUT)
            return {"success": False, "error": f"Control request timed out ({EXECUTOR_TIMEOUT}s)"}

    @property
    def connected(self) -> bool:
        """True if protocol is initialized (local IP set or cloud connected)."""
        if not self._protocol:
            return False
        try:
            return bool(getattr(self._protocol, "connected", False)) or bool(self._ip)
        except Exception:
            return False

    @property
    def auth_key(self) -> str | None:
        """Retrieve cloud auth_key from protocol if available."""
        if not self._protocol:
            return None
        key = getattr(self._protocol, "auth_key", None)
        if key:
            return key
        cloud = getattr(self._protocol, "cloud", None)
        if cloud:
            return getattr(cloud, "auth_key", None)
        return None

    def _connect_sync(self) -> bool:
        """Sync worker for connect(). Bootstraps Tasshack protocol with null token trick."""
        try:
            _bootstrap_protocol(self._ref_path)
        except Exception as e:
            logger.error("Bootstrap failed: %s", e)
            return False

        # Tasshack: local control requires (ip, token) with null token; prefer_cloud=False so
        # status/control use UDP miio, not Xiaomi cloud web RPC (unreliable for DreameHome).
        self._protocol = _protocol_cls(
            ip=self._ip,
            token=self._token,
            username=self._username,
            password=self._password,
            country=self._country,
            auth_key=self._auth_key,
            device_id=str(self._did) if self._did else None,
            prefer_cloud=False,
        )

        if self._username and self._password and self._protocol.cloud:
            ok = self._protocol.cloud.login()
            if ok:
                logger.info("Cloud login OK (maps / DID sync)")
                if self._did:
                    # Keep cloud session aligned with explicit DREAME_DID (do not trust stale localip).
                    self._protocol.cloud._did = str(self._did)
                else:
                    devices = self._protocol.cloud.get_devices()
                    if isinstance(devices, list) and devices:
                        target = _pick_cloud_device(devices, self._ip)
                        if target:
                            self._did = str(target.get("did", ""))
                            self._protocol.cloud._did = self._did
                            logger.info("Auto-discovered DID=%s (name=%s)", self._did, target.get("name", "?"))
            else:
                c = self._protocol.cloud
                why = "check DREAME_USER, DREAME_PASSWORD, DREAME_COUNTRY or account captcha/2FA"
                if getattr(c, "auth_failed", False):
                    why = "auth rejected (wrong password or expired session)"
                logger.warning("Cloud login failed; local-only (%s). For maps, fix cloud or set DREAME_DID.", why)

        self._apply_local_miot_tuning()

        if not self._protocol.connected and not self._ip:
            logger.error("No local IP and cloud not connected")
            return False

        if _map_manager_cls is not None:
            try:
                self._map_manager = _map_manager_cls(self._protocol)
                logger.info("Map manager initialized")
            except Exception as e:
                logger.warning("Map manager init failed: %s", e)

        if _map_renderer_cls is not None and self._map_renderer is None:
            try:
                try:
                    self._map_renderer = _map_renderer_cls(low_resolution=True, cache=True)
                except TypeError:
                    # Older / alternate Tasshack ref signatures (no low_resolution, etc.)
                    self._map_renderer = _map_renderer_cls()
            except Exception as e:
                logger.warning("DreameVacuumMapRenderer init failed: %s", e)

        logger.info("Connected [ip=%s null_token=%s did=%s]", self._ip, self._token == "0" * 32, self._did)
        return True

    def disconnect(self) -> None:
        """Tear down protocol; executor is kept for process lifetime (server exit)."""
        if self._protocol is not None:
            try:
                self._protocol.disconnect()
            except Exception as e:
                logger.warning("protocol.disconnect failed: %s", e)
        self._protocol = None
        self._map_manager = None
        self._map_renderer = None

    def _apply_local_miot_tuning(self) -> None:
        """DreameVacuumDeviceProtocol uses MiIOProtocol(..., timeout=2); slow Wi-Fi often needs more."""
        dev = getattr(self._protocol, "device", None)
        if not dev or not self._ip:
            return
        try:
            cur = int(getattr(dev, "_timeout", 5))
        except (TypeError, ValueError):
            cur = 5
        dev._timeout = max(cur, 10)
        logger.debug("Local miio socket timeout set to %s s (device was %s)", dev._timeout, cur)

    def local_miot_ready(self) -> bool:
        """True only after a successful local UDP miio discover (unrelated to DREAME_IP in env)."""
        dev = getattr(self._protocol, "device", None) if self._protocol else None
        return bool(dev) and bool(getattr(dev, "connected", False))

    def _get_status_sync(self) -> DreameStatus:
        if not self._protocol:
            return DreameStatus(error="Not connected")
        try:
            dids = _miot_did_slots(8, str(self._did) if self._did else None)
            bases = [
                _PROP_STATE,
                _PROP_ERROR,
                _PROP_BATTERY,
                _PROP_CHARGING,
                _PROP_STATUS,
                _PROP_TIME,
                _PROP_AREA,
                _PROP_FANSPEED,
            ]
            props = [{**b, "did": d} for b, d in zip(bases, dids, strict=True)]
            result = self._safe_call("get_properties", props)
            if result is None:
                return DreameStatus(
                    error=self._last_protocol_error or "No response from device",
                )

            raw = {f"{r['siid']}.{r['piid']}": r.get("value") for r in result if "value" in r}

            state_code = raw.get("2.1", 0)  # STATE
            battery = raw.get("3.1", 0)  # BATTERY_LEVEL
            charging_code = raw.get("3.2", 0)  # CHARGING_STATUS
            fan_speed = raw.get("4.4", 0)  # SUCTION_LEVEL
            time_s = raw.get("4.2", 0) or 0  # CLEANING_TIME
            area_cm2 = raw.get("4.3", 0) or 0  # CLEANED_AREA

            state_str = _STATE_MAP.get(state_code, f"state_{state_code}")
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

    def _control_sync(self, cmd: str) -> dict:
        if not self._protocol:
            return {"success": False, "error": "Not connected"}

        if cmd not in _ACTION_MAP:
            return {"success": False, "error": f"Unknown command: {cmd}"}
        # Tasshack DreameVacuumProtocol.action() encodes `did` as f"{siid}.{aiid}" in the
        # miio/miot request — it must not use the cloud numeric device id here.
        try:
            siid, aiid = _ACTION_MAP[cmd]
            result = self._safe_call("action", siid, aiid, [])
            if result is not None:
                return {"success": True, "message": f"Sent {cmd}", "result": result}
            return {
                "success": False,
                "error": self._last_protocol_error or f"No response for {cmd}",
            }
        except Exception as e:
            logger.exception("control(%s) failed", cmd)
            return {"success": False, "error": str(e)}

    def _safe_call(self, method: str, *args, **kwargs) -> Any:
        """Call protocol methods; for hybrid mode, also try ``protocol.cloud`` for file APIs."""
        if not self._protocol:
            return None

        func = getattr(self._protocol, method, None)
        cloud = getattr(self._protocol, "cloud", None)
        if func is None and method in {
            "get_device_file",
            "get_file",
            "get_file_url",
            "get_interim_file_url",
        }:
            if cloud is not None:
                func = getattr(cloud, method, None)
        if not func:
            logger.warning("Protocol object missing method: %s", method)
            return None

        try:
            out = func(*args, **kwargs)
            self._last_protocol_error = None
            return out
        except Exception as e:
            self._last_protocol_error = str(e)
            logger.error("Protocol call failed [%s]: %s", method, e)
            return None

    # ------------------------------------------------------------------
    # Map â€” the critical path that was hanging
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

    def _dreame_file_endpoints(self) -> list[Any]:
        """DreameHome file helpers often live on ``protocol.cloud`` in hybrid mode."""
        p = self._protocol
        if p is None:
            return []
        c = getattr(p, "cloud", None)
        out: list[Any] = []
        if c is not None:
            out.append(c)
        if c is not p:
            out.append(p)
        return out

    def _fetch_map_bytes_from_cloud_url(self, object_name: str) -> bytes | None:
        """Tasshack order: interim URL then get_file. Try cloud, then protocol."""
        for proto in self._dreame_file_endpoints():
            u: Any = None
            try:
                if hasattr(proto, "get_interim_file_url"):
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
                continue
            try:
                if not hasattr(proto, "get_file"):
                    continue
                raw = proto.get_file(str(u).strip())  # type: ignore[union-attr]
            except Exception as e:
                logger.debug("get_file(signed URL) on endpoint failed: %s", e)
                continue
            if not raw or _map_bytes_looks_like_error_json(raw):
                continue
            return raw
        return None

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
                "error": f"Map request timed out ({MAP_FETCH_TIMEOUT}s). DreameHome cloud may be unreachable.",
                "timeout": True,
            }

    def _get_map_sync(self) -> dict:
        with self._map_fetch_lock:
            if not self._protocol:
                return {"success": False, "error": "Not connected"}
            try:
                name_resolved = self._resolve_live_map_object_name()
                raw: bytes | None = None
                on_display: str | None = name_resolved
                attempted: list[dict[str, str]] = []
                ctry = getattr(self._protocol, "_country", None)
                if ctry is None and getattr(self._protocol, "cloud", None) is not None:
                    ctry = getattr(self._protocol.cloud, "_country", None)

                if name_resolved and str(name_resolved).strip("/"):
                    on_display = str(name_resolved).strip()
                    logger.info(
                        "Map fetch: object_name=%s (signed-URL first; get_device_file fallback)",
                        on_display,
                    )
                    raw = self._fetch_map_bytes_from_cloud_url(on_display)
                    if raw and not _map_bytes_looks_like_error_json(raw):
                        logger.info(
                            "Map fetch: %d bytes via signed-URL + get_file",
                            len(raw),
                        )
                        attempted.append(
                            {"step": "get_interim_file_url+get_file", "object_name": on_display or ""}
                        )
                    else:
                        raw = None
                    if not raw and on_display:
                        fail_count = 0
                        max_fails = 2
                        for file_type in ("map", 0):
                            if fail_count >= max_fails or raw is not None:
                                break
                            step = f"get_device_file:{file_type!s}"
                            attempted.append({"step": step, "object_name": on_display or ""})
                            chunk = self._safe_call("get_device_file", on_display, file_type)
                            if chunk is not None and not _map_bytes_looks_like_error_json(chunk):
                                raw = chunk
                                logger.info("Map fetch: %s -> %d bytes", step, len(raw or b""))
                                break
                            fail_count += 1

                if not raw:
                    logger.info("Map: trying property-based retrieval (siid=23, piid=1)")
                    try:
                        mslot = _miot_did_slots(1, str(self._did) if self._did else None)[0]
                        res = self._safe_call("get_properties", [{"did": mslot, "siid": 23, "piid": 1}])
                        if res and isinstance(res, list) and "value" in res[0]:
                            raw_val = res[0]["value"]
                            if isinstance(raw_val, str) and raw_val:
                                raw = base64.b64decode(raw_val)
                                on_display = "property_23_1"
                                logger.info("Map fetch: property 23.1 -> %d bytes", len(raw))
                    except Exception as e:
                        logger.warning("Property-based map fetch failed: %s", e)

                if (
                    not raw
                    and on_display
                    and not str(on_display).startswith("property_")
                ):
                    o = str(on_display).strip()
                    if o:
                        obj_for_url = o if o.startswith("/") else f"/{o}"
                        try:
                            url_data = self._safe_call("get_file_url", obj_for_url)
                            url = None
                            if isinstance(url_data, dict):
                                url = url_data.get("url") or url_data.get("fileUrl")
                            if isinstance(url, str) and url.strip():
                                raw = self._safe_call("get_file", url.strip())
                        except Exception as e:
                            logger.debug("get_file_url fallback: %s", e)

                if not raw or _map_bytes_looks_like_error_json(raw):
                    return {
                        "success": False,
                        "error": "Map fetch failed (signed URL, get_device_file, and property 23.1 all failed)",
                        "diagnostic_info": {
                            "did": str(self._did),
                            "object_name": on_display,
                            "country": ctry,
                            "attempted": attempted,
                            "hint": "Wake the robot, open the Dreame app, confirm DREAME_COUNTRY and DREAME_DID. "
                            "get_device_file can return 80001 when the cloud cannot reach the device.",
                        },
                    }

                result: dict[str, Any] = {
                    "success": True,
                    "object_name": on_display,
                    "raw_bytes": len(raw),
                }

                if _map_decoder_cls and self._map_renderer:
                    try:
                        raw_str = _map_raw_bytes_to_str(raw)
                        mm = self._map_manager
                        vslam = bool(getattr(mm, "_vslam_map", False)) if mm is not None else False
                        aes_iv = getattr(mm, "_aes_iv", None) if mm is not None else None
                        dec = _map_decoder_cls.decode_map(raw_str, vslam, 0, aes_iv, None)
                        mdl: Any = None
                        if isinstance(dec, tuple) and len(dec) > 0:
                            mdl = dec[0]
                        elif dec is not None:
                            mdl = dec
                        if mdl is not None:
                            out = self._map_renderer.render_map(mdl, 0, 0)
                            if out:
                                result["image"] = base64.b64encode(out).decode()
                            result["map_data"] = _map_object_to_dict(mdl)
                        else:
                            result["render_error"] = (
                                "decode_map returned no MapData (partial decode failed or wrong key)"
                            )
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
    """Tasshack `decode_map` expects a str; cloud files are typically UTF-8 or Latin-1-safe text."""
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


def _map_object_to_dict(map_data) -> dict[str, Any]:
    """Build REST map_data from a Tasshack decoded map object (rooms, path, areas, dimensions)."""
    d: dict[str, Any] = {
        "rooms": len(getattr(map_data, "segments", {}) or {}),
        "robot_position": _point_to_dict(getattr(map_data, "robot_position", None)),
        "charger_position": _point_to_dict(getattr(map_data, "charger_position", None)),
        "path": [_point_to_dict(p) for p in (getattr(map_data, "path", []) or [])],
        "virtual_walls": [
            {"p1": {"x": w.x0, "y": w.y0}, "p2": {"x": w.x1, "y": w.y1}}
            for w in (getattr(map_data, "virtual_walls", []) or [])
        ],
        "no_go_areas": [
            {
                "p1": {"x": a.x0, "y": a.y0},
                "p2": {"x": a.x1, "y": a.y1},
                "p3": {"x": a.x2, "y": a.y2},
                "p4": {"x": a.x3, "y": a.y3},
            }
            for a in (getattr(map_data, "no_go_areas", []) or [])
        ],
        "no_mop_areas": [
            {
                "p1": {"x": a.x0, "y": a.y0},
                "p2": {"x": a.x1, "y": a.y1},
                "p3": {"x": a.x2, "y": a.y2},
                "p4": {"x": a.x3, "y": a.y3},
            }
            for a in (getattr(map_data, "no_mop_areas", []) or [])
        ],
    }
    dim = getattr(map_data, "dimensions", None)
    d["dimensions"] = (
        {
            "top": getattr(dim, "top", 0),
            "left": getattr(dim, "left", 0),
            "height": getattr(dim, "height", 0),
            "width": getattr(dim, "width", 0),
            "grid_size": getattr(dim, "grid_size", 50),
        }
        if dim
        else None
    )
    return d


def _point_to_dict(point) -> dict | None:
    if point is None:
        return None
    return {"x": getattr(point, "x", 0), "y": getattr(point, "y", 0)}


def client_from_env() -> DreameHomeClient | None:
    """Build a DreameHomeClient from environment variables supporting Hybrid Mode."""
    load_dotenv()
    user = os.environ.get("DREAME_USER", "").strip()
    pwd = os.environ.get("DREAME_PASSWORD", "").strip()
    ip = os.environ.get("DREAME_IP", "").strip()
    token = os.environ.get("DREAME_TOKEN", "").strip()

    # Hybrid Mode Logic:
    # 1. Local-only: Must have IP (token is optional, defaults to 000... for circumvention)
    # 2. Cloud: Must have User + Password

    if not (user and pwd) and not ip:
        logger.warning("No credentials (cloud or local) set â€” running in stub mode")
        return None

    ref_raw = os.environ.get("DREAME_REF_PATH", "").strip()
    ref_path = Path(ref_raw) if ref_raw else _REF_DEFAULT

    return DreameHomeClient(
        username=user or None,
        password=pwd or None,
        ip=ip or None,
        token=token or None,
        country=os.environ.get("DREAME_COUNTRY", "eu").strip(),
        did=os.environ.get("DREAME_DID", "").strip() or None,
        auth_key=os.environ.get("DREAME_AUTH_KEY", "").strip() or None,
        ref_path=ref_path,
    )
