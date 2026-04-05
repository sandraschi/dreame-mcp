"""Portmanteau tool dreame(operation=...) for Dreame D20 Pro Plus (FastMCP 3.1).

Talks to DreameHome cloud via DreameHomeClient (no local token needed).
"""
from __future__ import annotations

import logging

from fastmcp import Context

from .state import _state

logger = logging.getLogger("dreame-mcp.portmanteau")


async def dreame_tool(
    ctx: Context | None = None,
    operation: str = "status",
    param1: str | float | None = None,
    param2: str | float | None = None,
    payload: dict | None = None,
) -> dict:
    """Unified control tool for Dreame robot vacuum (DreameHome cloud).

    Operations:
        status      — battery %, state, cleaning flag, cleaned area, time
        map         — fetch and decode LIDAR map (returns base64 PNG if rendering available)
        start_clean — start full clean
        stop        — stop cleaning
        pause       — pause cleaning
        go_home     — return to dock
        find_robot  — play sound to locate robot
        battery     — shortcut: battery % only

    Returns dict with success (bool). On failure includes error (str).
    """
    correlation_id = ctx.correlation_id if ctx and hasattr(ctx, "correlation_id") else "direct"
    op = operation.lower().strip()
    logger.info("dreame(%s) [%s]", op, correlation_id)

    client = _state.get("client")

    try:
        if op == "status":
            return await _status(client)

        if op == "battery":
            s = await _status(client)
            if s.get("success"):
                return {"success": True, "battery": s["battery"], "message": f"{s['battery']}%"}
            return s

        if op == "map":
            return await _map(client)

        if op in ("start_clean", "stop", "pause", "go_home", "find_robot"):
            return await _control(client, op)

        return {
            "success": False,
            "error": f"Unknown operation: {operation}. "
                     "Use: status, map, start_clean, stop, pause, go_home, find_robot, battery.",
        }

    except Exception as e:
        logger.exception("dreame(%s) unhandled error", op)
        return {"success": False, "error": str(e), "correlation_id": correlation_id}


async def _status(client) -> dict:
    if client is None:
        return _stub_status()
    st = await client.get_status()
    if st.error:
        return {"success": False, "error": st.error}
    return {
        "success": True,
        "battery": st.battery,
        "state": st.state,
        "is_charging": st.is_charging,
        "is_cleaning": st.is_cleaning,
        "cleaned_area_m2": st.cleaned_area,
        "cleaning_time_s": st.cleaning_time,
        "fan_speed": st.fan_speed,
    }


async def _map(client) -> dict:
    if client is None:
        return {
            "success": True,
            "message": "Stub — set DREAME_USER and DREAME_PASSWORD",
            "map": {},
        }
    result = await client.get_map()
    if not result.get("success"):
        return result
    out = {"success": True}
    if "image" in result:
        out["image"] = result["image"]          # base64 PNG
    if "map_data" in result:
        out["map_data"] = result["map_data"]
    if "raw_b64" in result:
        out["raw_b64"] = result["raw_b64"]      # raw map bytes fallback
    if "render_error" in result:
        out["render_error"] = result["render_error"]
    out["raw_bytes"] = result.get("raw_bytes", 0)
    return out


async def _control(client, cmd: str) -> dict:
    if client is None:
        return {"success": False, "error": "No client — set DREAME_USER and DREAME_PASSWORD"}
    return await client.control(cmd)


def _stub_status() -> dict:
    return {
        "success": True,
        "battery": 85,
        "state": "idle",
        "is_charging": False,
        "is_cleaning": False,
        "cleaned_area_m2": 0.0,
        "cleaning_time_s": 0,
        "fan_speed": "0",
        "message": "Stub — set DREAME_USER and DREAME_PASSWORD",
    }
