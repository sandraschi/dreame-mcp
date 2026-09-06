"""Portmanteau tool dreame(operation=...) for Dreame D20 Pro Plus (FastMCP 3.1).

Talks to DreameHome cloud via DreameHomeClient (no local token needed).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated, Literal

from fastmcp import Context
from pydantic import Field

from .state import _state

logger = logging.getLogger("dreame-mcp.portmanteau")

_DreameOperation = Literal[
    "status",
    "battery",
    "map",
    "start_clean",
    "stop",
    "pause",
    "go_home",
    "find_robot",
]


async def dreame_tool(
    ctx: Annotated[Context | None, Field(description="FastMCP sampling context (auto-injected).")] = None,
    operation: Annotated[
        _DreameOperation,
        Field(
            description="Operation to perform: status/battery/map telemetry or "
            "start_clean/stop/pause/go_home/find_robot control commands."
        ),
    ] = "status",
    param1: Annotated[
        str | float | None,
        Field(description="Optional operation parameter (unused by current operations)."),
    ] = None,
    param2: Annotated[
        str | float | None,
        Field(description="Optional second operation parameter (unused by current operations)."),
    ] = None,
    payload: Annotated[
        dict | None,
        Field(description="Optional structured payload (unused by current operations)."),
    ] = None,
) -> str:
    """Unified control tool for Dreame robot vacuum (DreameHome cloud).

    [RATIONALE] Consolidates telemetry (status, battery, map) and control
    (start_clean, stop, pause, go_home, find_robot) into one portmanteau so
    the agent surface stays compact and operations stay grouped by domain.

    ## Return Format
    Markdown summary for LLM context. Telemetry ops return section headers
    (## Dreame Robot Status / ## LIDAR Map Summary); control ops return
    "### Command executed" or "### Control failed" with the error text.

    ## Examples
    dreame_tool(operation="status")
    dreame_tool(operation="map")
    dreame_tool(operation="start_clean")
    """
    correlation_id = "direct"
    if ctx is not None:
        correlation_id = getattr(ctx, "correlation_id", None) or "direct"
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
                return f"### Battery: {data.get('battery')}%"
            return "### Battery: Unknown"

        if op == "map":
            data = await fetch_map_data(client)
            return _format_map_md(data)

        if op in ("start_clean", "stop", "pause", "go_home", "find_robot"):
            data = await execute_control_data(client, op)
            return _format_control_md(data, op)

        return (
            f"### Error: Unknown operation `{operation}`\n\n"
            "**Valid operations:**\n"
            "- `status`: Full telemetry\n"
            "- `map`: LIDAR map retrieval\n"
            "- `start_clean`, `stop`, `pause`, `go_home`, `find_robot`: Navigation & Control\n"
            "- `battery`: Quick battery check"
        )

    except Exception as e:
        logger.exception("dreame(%s) unhandled error", op)
        return f"### Error: crash in `dreame({op})`\n\n**Error:** {e}\n**ID:** `{correlation_id}`"


# ---------------------------------------------------------------------------
# Structured Data Fetchers (Shared with server.py API)
# ---------------------------------------------------------------------------


def offline_reasons() -> list[str]:
    """Honest why-control-is-down reasons from the startup snapshot.

    Distinguishes 'never configured' from 'configured but unreachable' —
    the old code blamed missing credentials for both.
    """
    if not _state.get("configured", False):
        return [
            "not configured: set DREAME_USER/DREAME_PASSWORD (cloud) or DREAME_IP (local) in .env, then restart the backend"
        ]
    conn = _state.get("connection", {}) or {}
    reasons: list[str] = []
    if conn.get("ip"):
        reasons.append(
            f"local path down: no miio answer at {conn['ip']}:54321 "
            "(robot off Wi-Fi, powered off, or IP changed — check the router)"
        )
    if conn.get("cloud_error"):
        reasons.append(f"cloud path down: {conn['cloud_error']}")
    if not reasons:
        reasons.append("no control path configured (set DREAME_IP or DREAME_USER/DREAME_PASSWORD)")
    return reasons


async def fetch_status_data(client) -> dict:
    if client is None:
        conn = _state.get("connection", {}) or {}
        return {
            "success": False,
            "error": ("Not configured. " if not _state.get("configured", False) else "Robot offline. ")
            + " | ".join(offline_reasons()),
            "unconfigured": not _state.get("configured", False),
            "offline": bool(_state.get("configured", False)),
            "ip": conn.get("ip"),
            "did": conn.get("did"),
        }
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
        return {"success": False, "error": "Disconnected - set DREAME_IP/TOKEN or DREAME_USER/PASSWORD."}
    return await client.get_map()


async def execute_control_data(client, cmd: str) -> dict:
    if client is None:
        return {"success": False, "error": "No client - check environment variables."}
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
        f"- **Cleaned Area:** {data.get('cleaned_area', 0)} m2",
        f"- **Cleaning Time:** {data.get('cleaning_time', 0) // 60}m {data.get('cleaning_time', 0) % 60}s",
        f"- **Charging:** {'[YES]' if data.get('is_charging') else '[NO]'}",
        f"- **Cleaning:** {'[ACTIVE]' if data.get('is_cleaning') else '[IDLE]'}",
        f"- **Fan Speed:** {data.get('fan_speed', '0')}",
    ]
    return "\n".join(lines)


def _format_map_md(data: dict) -> str:
    if not data.get("success"):
        error_msg = data.get("error", "Unknown error")
        return (
            f"### [MAP ERROR] Map Retrieval Failed\n\n**Error:** {error_msg}\n\n"
            "> [!TIP]\n> Ensure the robot has completed its first mapping run."
        )

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
        return f"### Command executed\n\n**Operation:** `{cmd}`\n**Message:** {data.get('message', 'Success')}"
    return f"### Control failed\n\n**Operation:** `{cmd}`\n**Error:** {data.get('error', 'Unknown error')}"
