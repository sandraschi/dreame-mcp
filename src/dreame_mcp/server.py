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
from fastapi.responses import JSONResponse
from fastmcp import FastMCP

from .agentic import dreame_agentic_workflow
from .client import client_from_env
from .portmanteau import (
    dreame_tool,
    execute_control_data,
    fetch_map_data,
    fetch_status_data,
)
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
            mode = "Hybrid" if (client._ip and client._username) else ("Local" if client._ip else "Cloud")
            logger.info("Dreame Protocol client connected [%s] (DID=%s)", mode, client._did)
            if client.auth_key:
                logger.info("Auth key available — set DREAME_AUTH_KEY=%s", client.auth_key[:30] + "…")
        else:
            logger.warning("Dreame Protocol connect failed — running in stub mode")
            _state["client"] = None
    else:
        logger.info("No credentials (DREAME_IP/TOKEN or USER/PWD) — running in stub mode")
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


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Catch-all for all crashes to prevent 502 Bad Gateway."""
    logger.exception("Global crash caught for %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal Server Error", "detail": str(exc), "service": "dreame-mcp"},
    )


mcp = FastMCP.from_fastapi(app, name="Dreame D20 Pro Plus")

# ---------------------------------------------------------------------------
# Help tool
# ---------------------------------------------------------------------------

_HELP_CATEGORIES = {
    "status": "Robot status (battery, state, area). dreame(operation='status').",
    "map": "LIDAR map image + room data. dreame(operation='map').",
    "control": "start_clean, stop, pause, go_home, find_robot. Supports Local (IP/Token) or Cloud.",
    "connection": "Set DREAME_IP/TOKEN (Local) or DREAME_USER/PASSWORD (Cloud).",
    "agentic": "dreame_agentic_workflow(goal=...) — LLM plans and executes multi-step goals via sampling.",
}


async def dreame_help(category: str | None = None, topic: str | None = None) -> dict:
    """Multi-level help for Dreame D20 Pro Plus MCP."""
    if not category:
        client = _state.get("client")
        mode = "stub"
        if client:
            mode = "hybrid" if (client._ip and client._username) else ("local" if client._ip else "cloud")
        return {
            "help": "Dreame D20 Pro Plus MCP (Local/Cloud Hybrid)",
            "connected": client is not None and client.connected,
            "mode": mode,
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
   # Local (Fastest, Circumvention)
   DREAME_IP=192.168.0.178
   DREAME_TOKEN=your_token

   # Cloud (Maps/Global)
   DREAME_USER=your@email.com
   DREAME_PASSWORD=yourpassword
   DREAME_COUNTRY=eu

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
4. dreame(operation='go_home') — Return to dock
5. dreame(operation='map') — LIDAR map retrieval
6. dreame_help(category='connection') — ENV reference
7. Dashboard: http://localhost:10795"""


# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------


@app.get("/api/v1/health")
async def health():
    client = _state.get("client")
    mode = "stub"
    if client:
        mode = "hybrid" if (client._ip and client._username) else ("local" if client._ip else "cloud")
    return {
        "status": "ok",
        "service": "dreame-mcp",
        "connected": client is not None and client.connected,
        "local_miot": client.local_miot_ready() if client else False,
        "mode": mode,
        "did": client._did if client else None,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/capabilities")
async def capabilities():
    """Industrial capability discovery for fleet managers."""
    return {
        "mcp_version": "3.2.0",
        "capabilities": {
            "tools": ["dreame", "dreame_help", "dreame_agentic_workflow"],
            "prompts": ["dreame_quick_start", "dreame_diagnostics"],
            "resources": [],
            "features": {
                "sampling": True,
                "agentic_workflow": True,
                "lidar_mapping": True,
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
            pixels = list(img.getdata())
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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    import argparse

    p = argparse.ArgumentParser(description="Dreame D20 Pro Plus MCP Server")
    p.add_argument("--mode", default="dual", choices=("stdio", "http", "dual"))
    p.add_argument("--port", type=int, default=int(os.environ.get("DREAME_MCP_PORT", "10794")))
    args = p.parse_args()

    if args.mode == "stdio":
        from fastmcp.cli import run_stdio

        run_stdio(mcp)
        return

    uvicorn.run(app, host="0.0.0.0", port=args.port)  # noqa: S104


if __name__ == "__main__":
    main()
