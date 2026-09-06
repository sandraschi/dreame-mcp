#!/usr/bin/env python3
"""Dreame D20 Pro Plus MCP Server — FastMCP 3.1, DreameHome cloud, sampling, agentic workflow."""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastmcp import FastMCP
from fastmcp.server.server import ToolResult  # type: ignore[attr-defined]

from .activity_log import ActivityLog, create_log_router, install_log_handler
from .agentic import dreame_agentic_workflow
from .client import DreameHomeClient, client_from_env
from .portmanteau import (
    dreame_tool,
    execute_control_data,
    fetch_map_data,
    fetch_status_data,
    offline_reasons,
)
from .state import _state

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("dreame-mcp")


def _mode(client) -> str:
    """Connection mode: hybrid/local/cloud when live, else unconfigured/offline."""
    if client:
        return "hybrid" if (client._ip and client._username) else ("local" if client._ip else "cloud")
    return "unconfigured" if not _state.get("configured", False) else "offline"


def _connection_snapshot(client) -> dict:
    """Startup snapshot so status stays honest when connect fails."""
    if client is None:
        return {"configured": False, "ip": None, "did": None, "has_cloud_creds": False, "cloud_error": None}
    return {
        "configured": True,
        "ip": client._ip,
        "did": client._did,
        "has_cloud_creds": bool(client._username and client._password),
        "cloud_error": client.cloud_error,
    }


def _repo_env_path() -> Path:
    """Repo-root .env — same file client_from_env() falls back to."""
    return Path(__file__).resolve().parent.parent.parent / ".env"


def _read_env_file(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines(keepends=True)
    except OSError:
        return []


def update_dotenv(values: dict[str, str], path: Path | None = None) -> Path:
    """Merge keys into the repo-root .env (atomic write, .bak backup).

    Only keys present in `values` are touched; comments, blank lines and all
    other entries are preserved. Missing keys are appended.
    """
    target = path or _repo_env_path()
    lines = _read_env_file(target)
    if target.is_file():
        backup = target.with_name(f"{target.name}.{datetime.now():%Y%m%d_%H%M%S}.bak")
        try:
            backup.write_bytes(target.read_bytes())
        except OSError:
            logger.warning("Could not back up %s before .env update", target)
    pending = dict(values)
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in pending:
                out.append(f"{key}={pending.pop(key)}\n")
                continue
        out.append(line)
    for key, value in pending.items():
        if not out or not out[-1].endswith("\n"):
            out.append("\n")
        out.append(f"{key}={value}\n")
    tmp = target.with_suffix(".tmp")
    tmp.write_text("".join(out), encoding="utf-8")
    tmp.replace(target)
    return target


async def _establish(client):
    """Connect one client and record the outcome in _state. Shared by lifespan
    startup and the Settings reconnect endpoint."""
    _state["configured"] = client is not None
    if client is None:
        _state["connection"] = _connection_snapshot(None)
        _state["startup_error"] = "No credentials (DREAME_IP/TOKEN or USER/PWD) — not configured"
        _state["client"] = None
        return
    ok = await client.connect()
    _state["connection"] = _connection_snapshot(client)
    if ok:
        _state["client"] = client
        _state["startup_error"] = None
        mode = "Hybrid" if (client._ip and client._username) else ("Local" if client._ip else "Cloud")
        logger.info("Dreame Protocol client connected [%s] (DID=%s)", mode, client._did)
        if client.auth_key:
            logger.debug("Auth key available (DREAME_AUTH_KEY set)")
    else:
        _state["client"] = None
        _state["startup_error"] = " | ".join(offline_reasons())
        logger.warning("Dreame Protocol connect failed — robot offline (%s)", _state["startup_error"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Dreame MCP starting")
    await _establish(client_from_env())

    yield

    logger.info("Dreame MCP shutting down")
    c = _state.get("client")
    if c:
        c.disconnect()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:10894",
        "http://127.0.0.1:10894",
        "http://localhost:10895",
        "http://127.0.0.1:10895",
        "http://tauri.localhost",
        "https://tauri.localhost",
        "tauri://localhost",
    ],
    allow_origin_regex=r"https?://(?:[a-zA-Z0-9-]+\.ts\.net|.*?\.tail-[a-f0-9]+\.ts\.net|tauri\.localhost|localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|100\.\d{1,3}\.\d{1,3}\.\d{1,3})(?::\d+)?$|^tauri://localhost$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mcp_log = ActivityLog()
install_log_handler(mcp_log)
mcp_log.add("INFO", "Dreame MCP activity log ready", kind="server", meta={"service": "dreame-mcp"})
app.include_router(create_log_router(mcp_log), prefix="/api")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Catch-all for all crashes to prevent 502 Bad Gateway."""
    logger.exception("Global crash caught for %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal Server Error", "detail": str(exc), "service": "dreame-mcp"},
    )


mcp = FastMCP.from_fastapi(app, name="Dreame D20 Pro Plus")

_READ_ONLY = {"readonly": True}
_MUTATING = {}

# ---------------------------------------------------------------------------
# Help tool
# ---------------------------------------------------------------------------

_HELP_CATEGORIES = {
    "status": "Robot status (battery, state, area). dreame_tool(operation='status').",
    "map": "LIDAR map image + room data. dreame_tool(operation='map').",
    "control": "start_clean, stop, pause, go_home, find_robot. Supports Local (IP/Token) or Cloud.",
    "connection": "Set DREAME_IP/TOKEN (Local) or DREAME_USER/PASSWORD (Cloud).",
    "agentic": "dreame_agentic_workflow(goal=...) — LLM plans and executes multi-step goals via sampling.",
}


async def dreame_help(category: str | None = None, topic: str | None = None) -> dict:
    """Multi-level help for Dreame D20 Pro Plus MCP.

    ## Return Format
    {"help": str, "connected": bool, "mode": str, "did": str|null,
     "categories": {category: description}} — or {"error": str, "available": [...]}
    for an unknown category.

    ## Examples
    dreame_help()
    dreame_help(category="status")
    """
    if not category:
        client = _state.get("client")
        conn = _state.get("connection", {}) or {}
        return {
            "help": "Dreame D20 Pro Plus MCP (Local/Cloud Hybrid)",
            "connected": client is not None and client.connected,
            "mode": _mode(client),
            "did": client._did if client else conn.get("did"),
            "categories": _HELP_CATEGORIES,
        }
    if category not in _HELP_CATEGORIES:
        return {"error": f"Unknown category: {category}", "available": list(_HELP_CATEGORIES.keys())}
    return {"category": category, "detail": _HELP_CATEGORIES[category]}


# ---------------------------------------------------------------------------
# Register MCP tools + prompts
# ---------------------------------------------------------------------------

mcp.tool(annotations=_MUTATING)(dreame_tool)
mcp.tool(annotations=_READ_ONLY)(dreame_help)
mcp.tool(annotations=_MUTATING)(dreame_agentic_workflow)


@mcp.tool(annotations=_READ_ONLY)
async def dreame_shutdown() -> dict:
    """Gracefully disconnect the Dreame client and stop the MCP server.

    ## Return Format
    {"success": bool, "message": str}

    ## Examples
    dreame_shutdown()
    """
    logger.info("dreame_shutdown requested")
    c = _state.get("client")
    if c:
        c.disconnect()
    _state["client"] = None
    if _server is not None:
        _server.should_exit = True
    return {"success": True, "message": "Dreame MCP shutting down"}


@mcp.tool(app=True, annotations=_READ_ONLY)
async def show_dreame_status_app() -> ToolResult:
    """Show live Dreame robot status as a rich card.

    ## Return Format
    ToolResult with a Prefab card (status, battery, state, charging, fan speed)
    plus a plain-text fallback.

    ## Examples
    show_dreame_status_app()
    """
    from prefab_ui import PrefabApp  # type: ignore[attr-defined]
    from prefab_ui.components import Heading, Row  # type: ignore[attr-defined]

    client = _state.get("client")
    if client is None:
        if not _state.get("configured", False):
            heading, detail = (
                "Not configured",
                "Set DREAME_USER/DREAME_PASSWORD or DREAME_IP in .env, then restart the backend.",
            )
        else:
            heading = "Offline"
            detail = " | ".join(offline_reasons())
        return ToolResult(
            content=f"Robot {heading.lower()} — {detail}",
            structured_content=PrefabApp(  # type: ignore[call-arg]
                title="Dreame Robot",
                components=[Heading(heading), Row(label="Status", value=detail)],  # type: ignore[call-arg]
            ),
        )
    try:
        st = await client.get_status()
    except Exception as e:
        return ToolResult(content=f"Status fetch failed: {e}")

    if st.error:
        return ToolResult(
            content=f"Status unavailable: {st.error}",
            structured_content=PrefabApp(  # type: ignore[call-arg]
                title="Dreame Robot",
                components=[Heading("Status unavailable"), Row(label="Error", value=st.error)],  # type: ignore[call-arg]
            ),
        )
    rows = [
        Row(label="State", value=str(st.state)),  # type: ignore[call-arg]
        Row(label="Battery", value=f"{st.battery}%"),  # type: ignore[call-arg]
        Row(label="Charging", value="YES" if st.is_charging else "NO"),  # type: ignore[call-arg]
        Row(label="Cleaning", value="ACTIVE" if st.is_cleaning else "IDLE"),  # type: ignore[call-arg]
        Row(label="Fan speed", value=str(st.fan_speed)),  # type: ignore[call-arg]
    ]
    content = (
        f"## Dreame Robot Status\n- State: {st.state}\n- Battery: {st.battery}%\n"
        f"- Charging: {'YES' if st.is_charging else 'NO'}\n"
        f"- Cleaning: {'ACTIVE' if st.is_cleaning else 'IDLE'}\n- Fan speed: {st.fan_speed}"
    )
    return ToolResult(
        content=content,
        structured_content=PrefabApp(title="Dreame Robot", components=[Heading("Live status"), *rows]),  # type: ignore[call-arg]
    )


@mcp.prompt
def dreame_quick_start() -> str:
    """Setup and connect instructions for Dreame D20 Pro Plus."""
    return """You are helping set up the Dreame D20 Pro Plus MCP server.

This server uses the DreameHome cloud API — no local token required.

1. Set environment variables:
   # Local (Fastest, Circumvention)
   DREAME_IP=192.168.0.178
   DREAME_TOKEN=your_token

   # Cloud (Maps/Global)
   DREAME_USER=your@email.com
   DREAME_PASSWORD=yourpassword
   DREAME_COUNTRY=eu

   DREAME_REF_PATH=D:/Dev/repos/external/tasshack_dreame_vacuum_ref

2. Start server: uv run python -m dreame_mcp --mode dual --port 10894
3. Open dashboard: http://localhost:10895
4. MCP client: dreame_tool(operation='status') then dreame_tool(operation='start_clean')
5. Agentic: dreame_agentic_workflow(goal='clean the living room then return to dock')"""


@mcp.prompt
def dreame_diagnostics() -> str:
    """Diagnostic checklist for Dreame D20 Pro Plus."""
    return """Run a quick diagnostic:

1. GET /api/v1/health — check connected: true, DID present
2. dreame_tool(operation='status') — battery and state
3. dreame_tool(operation='start_clean') — confirmed working
4. dreame_tool(operation='go_home') — Return to dock
5. dreame_tool(operation='map') — LIDAR map retrieval
6. dreame_help(category='connection') — ENV reference
7. Dashboard: http://localhost:10895"""


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@mcp.resource("dreame://status")
async def dreame_status_resource() -> str:
    """Live Dreame robot status as Markdown (read via resource://)."""
    client = _state.get("client")
    if client is None:
        if not _state.get("configured", False):
            return "**Robot:** not configured (set DREAME_USER/DREAME_PASSWORD or DREAME_IP in .env)"
        return "**Robot offline:** " + " | ".join(offline_reasons())
    st = await client.get_status()
    if st.error:
        return f"**Status unavailable:** {st.error}"
    return (
        f"**State:** {st.state} | **Battery:** {st.battery}% | "
        f"**Charging:** {'yes' if st.is_charging else 'no'} | "
        f"**Cleaning:** {'active' if st.is_cleaning else 'idle'}"
    )


# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------


@app.get("/api/v1/health")
async def health():
    client = _state.get("client")
    conn = _state.get("connection", {}) or {}
    control = _control_status(client)
    return {
        "status": "ok",
        "service": "dreame-mcp",
        "connected": client is not None and client.connected,
        "local_miot": client.local_miot_ready() if client else False,
        "mode": _mode(client),
        "did": client._did if client else conn.get("did"),
        "control": control,
        "cloud_error": getattr(client, "cloud_error", None) if client else conn.get("cloud_error"),
        "startup_error": _state.get("startup_error"),
        "timestamp": datetime.now().isoformat(),
    }


def _control_status(client) -> dict:
    """Why control may be unavailable right now — one of the most-asked questions."""
    if client is None:
        reasons = offline_reasons()
        out: dict = {"available": False, "reason": " | ".join(reasons)}
        out["unconfigured"] = not _state.get("configured", False)
        out["offline"] = bool(_state.get("configured", False))
        return out
    local_ok = client.local_miot_ready()
    cloud_ok = bool(getattr(client, "cloud_error", None) is None and client._username)
    if local_ok:
        return {"available": True, "path": "local (UDP miio)"}
    if cloud_ok and client.connected:
        return {"available": True, "path": "cloud (DreameHome)"}
    reasons = []
    if not local_ok and client._ip:
        reasons.append(
            "local path down: robot did not answer UDP miio at "
            f"{client._ip}:54321 — check the robot is powered on, on Wi-Fi, "
            "and its IP (run `just check-discovery`)."
        )
    if client._username and getattr(client, "cloud_error", None):
        reasons.append(str(client.cloud_error))
    if not reasons:
        reasons.append("no control path configured (set DREAME_IP or DREAME_USER/DREAME_PASSWORD)")
    return {"available": False, "reason": " | ".join(reasons)}


@app.get("/api/capabilities")
async def capabilities():
    """Industrial capability discovery for fleet managers."""
    return {
        "mcp_version": "3.2.0",
        "capabilities": {
            "tools": [
                "dreame_tool",
                "dreame_help",
                "dreame_agentic_workflow",
                "dreame_shutdown",
                "show_dreame_status_app",
            ],
            "prompts": ["dreame_quick_start", "dreame_diagnostics"],
            "resources": ["dreame://status"],
            "features": {
                "sampling": True,
                "agentic_workflow": True,
                "lidar_mapping": True,
                "prefab_ui": True,
            },
        },
        "endpoints": {
            "health": "/api/v1/health",
            "status": "/api/v1/status",
            "map": "/api/v1/map",
            "map_png": "/api/v1/map/png",
        },
    }


@app.get("/api/v1/status")
async def api_status():
    try:
        client = _state.get("client")
        out = await fetch_status_data(client)
        if not out.get("success"):
            return JSONResponse(status_code=502, content=out)
        return out
    except Exception as e:
        logger.exception("Route status failed")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


def _connection_info() -> dict:
    """Public connection snapshot for Settings — never includes secrets."""
    client = _state.get("client")
    conn = _state.get("connection", {}) or {}
    return {
        "mode": _mode(client),
        "connected": client is not None and client.connected,
        "configured": bool(_state.get("configured", False)),
        "ip": client._ip if client else conn.get("ip"),
        "did": client._did if client else conn.get("did"),
        "user": (client._username or None) if client else None,
        "user_set": bool((client._username if client else None) or os.environ.get("DREAME_USER")),
        "password_set": bool(os.environ.get("DREAME_PASSWORD")),
        "country": os.environ.get("DREAME_COUNTRY", "eu") or "eu",
        "cloud_error": getattr(client, "cloud_error", None) if client else conn.get("cloud_error"),
        "startup_error": _state.get("startup_error"),
    }


@app.get("/api/v1/connection")
async def api_connection_get():
    return _connection_info()


def _file_env() -> dict[str, str]:
    """Current .env values (file truth — process env may be narrower)."""
    values: dict[str, str] = {}
    for line in _read_env_file(_repo_env_path()):
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key, _, value = stripped.partition("=")
            values[key.strip()] = value.strip()
    return values


@app.post("/api/v1/connection/test")
async def api_connection_test(payload: dict):
    """Dry-run: try the given (or currently stored) settings WITHOUT saving.

    Merges the body over the .env file values in memory only, connects a
    throwaway client, then disconnects. Nothing is written, _state untouched.
    NOTE: a test with a wrong cloud password still costs one login attempt.
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON object expected")
    allowed = {"ip", "user", "password", "country"}
    unknown = set(payload) - allowed
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown keys: {sorted(unknown)}")
    file_env = _file_env()

    def pick(form_key: str, env_key: str, default: str = "") -> str:
        raw = payload.get(form_key)
        if raw is not None and str(raw).strip():
            return str(raw).strip()
        return file_env.get(env_key, default)

    probe = DreameHomeClient(
        username=pick("user", "DREAME_USER") or None,
        password=pick("password", "DREAME_PASSWORD") or None,
        country=pick("country", "DREAME_COUNTRY", "eu") or "eu",
        ip=pick("ip", "DREAME_IP") or None,
        token=file_env.get("DREAME_TOKEN") or None,
        did=file_env.get("DREAME_DID") or None,
        auth_key=file_env.get("DREAME_AUTH_KEY") or None,
        ref_path=Path(file_env["DREAME_REF_PATH"]) if file_env.get("DREAME_REF_PATH") else None,
    )
    try:
        ok = await probe.connect()
    finally:
        try:
            probe.disconnect()
        except Exception:
            pass
    if ok:
        return {"success": True, "mode": _mode(probe), "did": probe._did}
    reasons = []
    if probe._ip:
        reasons.append(f"no miio answer at {probe._ip}:54321")
    if probe.cloud_error:
        reasons.append(str(probe.cloud_error))
    return {"success": False, "error": " | ".join(reasons) or "connect failed", "did": probe._did}


@app.post("/api/v1/connection")
async def api_connection_update(payload: dict):
    """Update connection settings (DREAME_IP/USER/PASSWORD/COUNTRY) and reconnect.

    Only keys present in the body are changed; an empty password means
    "leave unchanged". Persists to the repo-root .env, applies to the live
    process env, then reconnects. Returns the new connection snapshot.
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON object expected")
    allowed = {"ip", "user", "password", "country"}
    unknown = set(payload) - allowed
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown keys: {sorted(unknown)}")
    env_map = {"ip": "DREAME_IP", "user": "DREAME_USER", "password": "DREAME_PASSWORD", "country": "DREAME_COUNTRY"}
    updates: dict[str, str] = {}
    for key in allowed:
        if key not in payload or payload[key] is None:
            continue
        value = str(payload[key]).strip()
        if key == "password" and not value:
            continue  # empty password = leave unchanged
        updates[env_map[key]] = value
    if not updates:
        return {"updated": [], "connection": _connection_info()}
    try:
        saved = update_dotenv(updates)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Could not write .env: {e}") from e
    for env_key, value in updates.items():
        os.environ[env_key] = value
    old = _state.get("client")
    if old:
        try:
            old.disconnect()
        except Exception:
            pass
    logger.info("Connection settings updated (%s) — reconnecting", sorted(updates))
    await _establish(client_from_env())
    info = _connection_info()
    return {"updated": sorted(updates), "env_file": str(saved), "connection": info}


@app.get("/api/v1/map")
async def api_map():
    try:
        client = _state.get("client")
        out = await fetch_map_data(client)
        if not out.get("success"):
            return JSONResponse(status_code=502, content=out)
        return out
    except Exception as e:
        logger.exception("Route map failed")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@app.get("/api/v1/map/png")
async def api_map_png():
    """Download rendered map as PNG image (direct binary, not JSON-wrapped).

    Returns the Tasshack-rendered floor plan PNG if available.
    Consumers: webapp <img> src, robotics-mcp, yahboom-mcp pipelines.
    """
    from fastapi.responses import Response

    from .map_export import map_response_to_png_bytes

    client = _state.get("client")
    out = await fetch_map_data(client)
    if not out.get("success"):
        raise HTTPException(status_code=502, detail=out.get("error", "Map unavailable"))
    png = map_response_to_png_bytes(out)
    if png is None:
        raise HTTPException(status_code=404, detail="No rendered PNG available (render_error or deps missing)")
    return Response(
        content=png,
        media_type="image/png",
        headers={
            "Content-Disposition": "inline; filename=dreame_map.png",
        },
    )


@app.get("/api/v1/map/pgm")
async def api_map_pgm():
    """Export map as PGM — ROS2 nav2_map_server standard format.

    This is the raw occupancy grid image. Use with /api/v1/map/yaml for
    a complete ROS2 map_server compatible map pair.

    Note: Requires Tasshack map manager to decode rooms/grid. If decode
    fails, returns 404 — use /api/v1/map for raw_b64 fallback.
    """
    from fastapi.responses import Response

    from .map_export import occupancy_to_pgm

    client = _state.get("client")
    out = await fetch_map_data(client)
    if not out.get("success"):
        raise HTTPException(status_code=502, detail=out.get("error", "Map unavailable"))

    # If we have rendered image, convert PNG → grayscale → PGM.
    # For now, use the rendered PNG dimensions if available.
    png_bytes = None
    if "image" in out:
        try:
            import base64

            from PIL import Image

            png_bytes = base64.b64decode(out["image"])
            img = Image.open(__import__("io").BytesIO(png_bytes)).convert("L")
            w, h = img.size
            # Convert to OccupancyGrid convention: white(255)=free(0), black(0)=occupied(100)
            pixels = list(img.getdata())  # type: ignore[arg-type]
            occupancy = []
            for p in pixels:
                if p > 250:
                    occupancy.append(0)  # free
                elif p < 10:
                    occupancy.append(100)  # occupied
                else:
                    occupancy.append(-1)  # unknown
            pgm = occupancy_to_pgm(occupancy, w, h)
            return Response(
                content=pgm,
                media_type="application/octet-stream",
                headers={
                    "Content-Disposition": "attachment; filename=dreame_map.pgm",
                },
            )
        except Exception as e:
            logger.debug("PGM export path failed: %s", e)

    raise HTTPException(status_code=404, detail="Cannot export PGM: map rendering unavailable")


@app.get("/api/v1/map/yaml")
async def api_map_yaml():
    """Export map YAML metadata — ROS2 nav2_map_server companion to PGM.

    Returns the YAML file that nav2_map_server loads alongside the PGM.
    Default resolution: 0.05 m/pixel (standard for indoor SLAM).
    """
    from fastapi.responses import Response

    from .map_export import occupancy_to_yaml

    yaml_str = occupancy_to_yaml(
        image_filename="dreame_map.pgm",
        resolution=0.05,
        origin=(0.0, 0.0, 0.0),
    )
    return Response(
        content=yaml_str,
        media_type="text/yaml",
        headers={
            "Content-Disposition": "attachment; filename=dreame_map.yaml",
        },
    )


@app.post("/api/v1/control/{cmd}")
async def api_control(cmd: str):
    valid = ("start_clean", "stop", "pause", "go_home", "find_robot")
    if cmd not in valid:
        raise HTTPException(status_code=400, detail=f"Unknown command: {cmd}. Valid: {valid}")
    client = _state.get("client")
    out = await execute_control_data(client, cmd)
    if not out.get("success"):
        raise HTTPException(status_code=502, detail=out.get("error", "Control failed"))
    return out


@app.get("/api/v1/diagnostics")
async def api_diagnostics():
    """Full diagnostics for CUA-NSIS smoke testing: tools, system info, errors."""
    import platform

    client = _state.get("client")
    return {
        "status": "ok",
        "server": "dreame-mcp",
        "version": "0.2.0",
        "uptime_seconds": 0,
        "tool_count": 5,
        "tools": [
            {"name": "dreame_tool"},
            {"name": "dreame_help"},
            {"name": "dreame_agentic_workflow"},
            {"name": "dreame_shutdown"},
            {"name": "show_dreame_status_app"},
        ],
        "system": {
            "platform": platform.system(),
            "python": platform.python_version(),
            "connected": client is not None and client.connected,
            "mode": _mode(client),
        },
        "errors": [],
    }


@app.post("/api/v1/shutdown")
async def api_shutdown():
    """Graceful shutdown of the server (used by the MCP shutdown tool)."""
    out = await dreame_shutdown()
    return out


@app.get("/api/skills")
async def api_skills():
    """List available skills (skill:// resources) for skill-first chat."""
    skills_dir = Path(__file__).parent / "skills"
    if not skills_dir.is_dir():
        return {"skills": []}
    names = sorted(d.name for d in skills_dir.iterdir() if (d / "SKILL.md").is_file())
    return {"skills": [{"name": n, "uri": f"skill://{n}/SKILL.md"} for n in names]}


# ---------------------------------------------------------------------------
# LLM Chat endpoints (Ollama proxy)
# ---------------------------------------------------------------------------

import httpx

OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")


@app.get("/api/llm/providers")
async def llm_providers():
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"{OLLAMA_BASE}/api/tags")
            r.raise_for_status()
            data = r.json()
            models = [m["name"] for m in data.get("models", [])]
    except Exception:
        models = []
    return {"providers": [{"name": "ollama", "models": models}]}


@app.post("/api/llm/chat")
async def llm_chat(body: dict):
    prompt = body.get("prompt", "")
    model = body.get("model", "llama3.2:3b")
    if not prompt:
        return {"error": "Missing prompt"}
    try:
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.post(
                f"{OLLAMA_BASE}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
            )
            r.raise_for_status()
            data = r.json()
            return {"response": data.get("response", "")}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

_server: uvicorn.Server | None = None


def main():
    import argparse

    p = argparse.ArgumentParser(description="Dreame D20 Pro Plus MCP Server")
    p.add_argument("--mode", default="dual", choices=("stdio", "http", "dual"))
    p.add_argument("--port", type=int, default=int(os.environ.get("DREAME_MCP_PORT", "10894")))
    args = p.parse_args()

    if args.mode == "stdio":
        import asyncio

        asyncio.run(mcp.run_stdio_async())
        return

    global _server
    bind_host = os.environ.get("DREAME_MCP_HOST", "127.0.0.1")
    config = uvicorn.Config(app, host=bind_host, port=args.port, log_level="info")
    _server = uvicorn.Server(config)
    _server.run()


if __name__ == "__main__":
    main()
