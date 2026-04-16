"""Portmanteau tool dreame(operation=...) for Dreame D20 Pro Plus (FastMCP 3.1).

Talks to DreameHome cloud via DreameHomeClient (no local token needed).
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastmcp import Context

from .state import _state

logger = logging.getLogger("dreame-mcp.portmanteau")


async def dreame_tool(
    ctx: Context | None = None,
    operation: str = "status",
    param1: str | float | None = None,
    param2: str | float | None = None,
    payload: dict | None = None,
) -> str:
    """Unified control tool for Dreame robot vacuum (DreameHome cloud).
    Returns Markdown summary for LLM context.
    """
    correlation_id = ctx.correlation_id if ctx and hasattr(ctx, "correlation_id") else "direct"
    op = operation.lower().strip()
    logger.info("dreame(%s) [%s]", op, correlation_id)

    client = _state.get("client")

    try:
        if op == "status":
            data = await fetch_status_data(client)
            return _format_status_md(data)

        if op == "battery":
            data = await fetch_status_data(client)
            if data.get("success"):
                return f"### ðŸ”‹ Battery: {data.get('battery')}%"
            return "### ðŸ”‹ Battery: Unknown"

        if op == "map":
            data = await fetch_map_data(client)
            return _format_map_md(data)

        if op in ("start_clean", "stop", "pause", "go_home", "find_robot"):
            data = await execute_control_data(client, op)
            return _format_control_md(data, op)

        return (
            f"### âŒ Error: Unknown operation `{operation}`\n\n"
            "**Valid operations:**\n"
            "- `status`: Full telemetry\n"
            "- `map`: LIDAR map retrieval\n"
            "- `start_clean`, `stop`, `pause`, `go_home`, `find_robot`: Navigation & Control\n"
            "- `battery`: Quick battery check"
        )

    except Exception as e:
        logger.exception("dreame(%s) unhandled error", op)
        return f"### ðŸš¨ Crash in `dreame({op})`\n\n**Error:** {e}\n**ID:** `{correlation_id}`"


# ---------------------------------------------------------------------------
# Structured Data Fetchers (Shared with server.py API)
# ---------------------------------------------------------------------------


async def fetch_status_data(client) -> dict:
    if client is None:
        return _stub_status()
    st = await client.get_status()
    if st.error:
        return {"success": False, "error": st.error}

    return {
        "success": True,
        "state": st.state,
        "battery": st.battery,
        "cleaned_area": st.cleaned_area,
        "cleaning_time": st.cleaning_time,
        "is_charging": st.is_charging,
        "is_cleaning": st.is_cleaning,
        "fan_speed": st.fan_speed,
        "timestamp": datetime.now().isoformat(),
    }


async def fetch_map_data(client) -> dict:
    if client is None:
        return {"success": False, "error": "Disconnected â€” Set DREAME_IP/TOKEN or USER/PWD."}
    return await client.get_map()


async def execute_control_data(client, cmd: str) -> dict:
    if client is None:
        return {"success": False, "error": "No client â€” Check environment variables."}
    return await client.control(cmd)


# ---------------------------------------------------------------------------
# Markdown Formatters (For AI/MCP context)
# ---------------------------------------------------------------------------


def _format_status_md(data: dict) -> str:
    if not data.get("success"):
        return f"### [ERROR]\n\n{data.get('error', 'Unknown error')}"

    # Use .get() with defaults for all telemetry
    lines = [
        "## Dreame Robot Status",
        f"- **State:** {str(data.get('state', 'unknown')).capitalize()}",
        f"- **Battery:** {data.get('battery', 0)}%",
        f"- **Cleaned Area:** {data.get('cleaned_area', 0)} mÂ²",
        f"- **Cleaning Time:** {data.get('cleaning_time', 0) // 60}m {data.get('cleaning_time', 0) % 60}s",
        f"- **Charging:** {'[YES]' if data.get('is_charging') else '[NO]'}",
        f"- **Cleaning:** {'[ACTIVE]' if data.get('is_cleaning') else '[IDLE]'}",
        f"- **Fan Speed:** {data.get('fan_speed', '0')}",
    ]
    return "\n".join(lines)


def _format_map_md(data: dict) -> str:
    if not data.get("success"):
        error_msg = data.get("error", "Unknown error")
        return f"### [MAP ERROR] Map Retrieval Failed\n\n**Error:** {error_msg}\n\n> [!TIP]\n> Ensure the robot has completed its first mapping run."

    lines = [
        "## LIDAR Map Summary",
        f"- **Object Name:** `{data.get('object_name', 'None')}`",
        f"- **Raw Size:** {data.get('raw_bytes', 0) / 1024:.1f} KB",
    ]

    md = data.get("map_data")
    if isinstance(md, dict):
        lines.append(f"- **Rooms Detected:** {md.get('rooms', 0)}")
        pos = md.get("robot_position")
        if pos:
            lines.append(f"- **Robot Position:** ({pos.get('x', 0)}, {pos.get('y', 0)})")
        
        path = md.get("path", [])
        if path:
            lines.append(f"- **Movement Trail:** {len(path)} points")

        vw = md.get("virtual_walls", [])
        nga = md.get("no_go_areas", [])
        nma = md.get("no_mop_areas", [])
        if vw or nga or nma:
            lines.append(f"- **Restricted Zones:** {len(vw)} Walls, {len(nga)} No-Go, {len(nma)} No-Mop")

    if "image" in data:
        lines.append("\n> [!NOTE]\n> Image data received. Use the webapp to view the full rendered map.")

    if data.get("render_error"):
        lines.append(f"\n> [!WARNING]\n> Render error: {data['render_error']}")

    return "\n".join(lines)


def _format_control_md(data: dict, cmd: str) -> str:
    if data.get("success"):
        return f"### âœ… Command Executed\n\n**Operation:** `{cmd}`\n**Message:** {data.get('message', 'Success')}"
    return f"### âŒ Control Failed\n\n**Operation:** `{cmd}`\n**Error:** {data.get('error', 'Unknown error')}"


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
        "message": "Stub â€” set DREAME_USER and DREAME_PASSWORD",
    }
