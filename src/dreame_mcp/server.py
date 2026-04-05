#!/usr/bin/env python3
"""Dreame D20 Pro Plus MCP Server — FastMCP 3.1, DreameHome cloud, sampling, agentic workflow."""
from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import FastMCP

from .agentic import dreame_agentic_workflow
from .client import client_from_env
from .portmanteau import dreame_tool
from .state import _state

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("dreame-mcp")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Dreame MCP starting")
    client = client_from_env()
    if client:
        ok = await client.connect()
        if ok:
            _state["client"] = client
            logger.info("DreameHome client connected (DID=%s)", client._did)
            # Persist auth_key so it can be reused across restarts
            if client.auth_key:
                logger.info("Auth key refreshed — set DREAME_AUTH_KEY=%s", client.auth_key[:30] + "…")
        else:
            logger.warning("DreameHome connect failed — running in stub mode")
            _state["client"] = None
    else:
        logger.info("No credentials — running in stub mode (set DREAME_USER + DREAME_PASSWORD)")
        _state["client"] = None

    yield

    logger.info("Dreame MCP shutting down")
    c = _state.get("client")
    if c:
        c.disconnect()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

mcp = FastMCP.from_fastapi(app, name="Dreame D20 Pro Plus")

# ---------------------------------------------------------------------------
# Help tool
# ---------------------------------------------------------------------------

_HELP_CATEGORIES = {
    "status":     "Robot status (battery, state, area). dreame(operation='status').",
    "map":        "LIDAR map image + room data. dreame(operation='map'). Returns base64 PNG when map rendering is available.",
    "control":    "start_clean, stop, pause, go_home, find_robot. Requires DREAME_USER + DREAME_PASSWORD.",
    "connection": "Set DREAME_USER, DREAME_PASSWORD, DREAME_COUNTRY (eu), DREAME_DID (optional).",
    "agentic":    "dreame_agentic_workflow(goal=...) — LLM plans and executes multi-step goals via sampling.",
}


async def dreame_help(category: str | None = None, topic: str | None = None) -> dict:
    """Multi-level help for Dreame D20 Pro Plus MCP."""
    if not category:
        client = _state.get("client")
        return {
            "help": "Dreame D20 Pro Plus MCP (DreameHome cloud)",
            "connected": client is not None and client.connected,
            "did": client._did if client else None,
            "categories": _HELP_CATEGORIES,
        }
    if category not in _HELP_CATEGORIES:
        return {"error": f"Unknown category: {category}", "available": list(_HELP_CATEGORIES.keys())}
    return {"category": category, "detail": _HELP_CATEGORIES[category]}


# ---------------------------------------------------------------------------
# Register MCP tools + prompts
# ---------------------------------------------------------------------------

mcp.tool()(dreame_tool)
mcp.tool()(dreame_help)
mcp.tool()(dreame_agentic_workflow)


@mcp.prompt
def dreame_quick_start() -> str:
    """Setup and connect instructions for Dreame D20 Pro Plus."""
    return """You are helping set up the Dreame D20 Pro Plus MCP server.

This server uses the DreameHome cloud API — no local token required.

1. Set environment variables:
   DREAME_USER=your@email.com
   DREAME_PASSWORD=yourpassword
   DREAME_COUNTRY=eu          (or cn, us, etc.)
   DREAME_DID=2045852486      (optional — auto-discovered if single device)
   DREAME_AUTH_KEY=...        (optional — reuse token from previous login)
   DREAME_REF_PATH=D:/Dev/repos/tasshack_dreame_vacuum_ref

2. Start server: uv run python -m dreame_mcp --mode dual --port 10794
3. Open dashboard: http://localhost:10795
4. MCP client: dreame(operation='status') then dreame(operation='start_clean')
5. Agentic: dreame_agentic_workflow(goal='clean the living room then return to dock')"""


@mcp.prompt
def dreame_diagnostics() -> str:
    """Diagnostic checklist for Dreame D20 Pro Plus."""
    return """Run a quick diagnostic:

1. GET /api/v1/health — check connected: true, DID present
2. dreame(operation='status') — battery and state
3. dreame(operation='start_clean') — confirmed working
4. dreame(operation='go_home') — NOTE: currently not working (action ID unverified)
   Workaround: dock via DreameHome app manually
5. dreame(operation='map') — requires MQTT connection; raw_b64 always returned
6. dreame_help(category='connection') — env var reference
7. Dashboard: http://localhost:10895"""


# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------

@app.get("/api/v1/health")
async def health():
    client = _state.get("client")
    return {
        "status": "ok",
        "service": "dreame-mcp",
        "connected": client is not None and client.connected,
        "did": client._did if client else None,
        "cloud": "DreameHome",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/v1/status")
async def api_status():
    out = await dreame_tool(ctx=None, operation="status")
    if not out.get("success"):
        raise HTTPException(status_code=502, detail=out.get("error", "Status unavailable"))
    return out


@app.get("/api/v1/map")
async def api_map():
    out = await dreame_tool(ctx=None, operation="map")
    if not out.get("success"):
        raise HTTPException(status_code=502, detail=out.get("error", "Map unavailable"))
    return out


@app.get("/api/v1/map/png")
async def api_map_png():
    """Download rendered map as PNG image (direct binary, not JSON-wrapped).

    Returns the Tasshack-rendered floor plan PNG if available.
    Consumers: webapp <img> src, robotics-mcp, yahboom-mcp pipelines.
    """
    from fastapi.responses import Response

    from .map_export import map_response_to_png_bytes

    out = await dreame_tool(ctx=None, operation="map")
    if not out.get("success"):
        raise HTTPException(status_code=502, detail=out.get("error", "Map unavailable"))
    png = map_response_to_png_bytes(out)
    if png is None:
        raise HTTPException(status_code=404, detail="No rendered PNG available (render_error or deps missing)")
    return Response(content=png, media_type="image/png", headers={
        "Content-Disposition": "inline; filename=dreame_map.png",
    })


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

    out = await dreame_tool(ctx=None, operation="map")
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
            pixels = list(img.getdata())
            occupancy = []
            for p in pixels:
                if p > 250:
                    occupancy.append(0)       # free
                elif p < 10:
                    occupancy.append(100)     # occupied
                else:
                    occupancy.append(-1)      # unknown
            pgm = occupancy_to_pgm(occupancy, w, h)
            return Response(content=pgm, media_type="application/octet-stream", headers={
                "Content-Disposition": "attachment; filename=dreame_map.pgm",
            })
        except Exception:
            pass

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
    return Response(content=yaml_str, media_type="text/yaml", headers={
        "Content-Disposition": "attachment; filename=dreame_map.yaml",
    })


@app.post("/api/v1/control/{cmd}")
async def api_control(cmd: str):
    valid = ("start_clean", "stop", "pause", "go_home", "find_robot")
    if cmd not in valid:
        raise HTTPException(status_code=400, detail=f"Unknown command: {cmd}. Valid: {valid}")
    out = await dreame_tool(ctx=None, operation=cmd)
    if not out.get("success"):
        raise HTTPException(status_code=502, detail=out.get("error", "Control failed"))
    return out


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    import argparse
    p = argparse.ArgumentParser(description="Dreame D20 Pro Plus MCP Server")
    p.add_argument("--mode", default="dual", choices=("stdio", "http", "dual"))
    p.add_argument("--port", type=int, default=int(os.environ.get("DREAME_MCP_PORT", "10894")))
    args = p.parse_args()

    if args.mode == "stdio":
        from fastmcp.cli import run_stdio
        run_stdio(mcp)
        return

    uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
