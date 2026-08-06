"""Agentic workflow for Dreame robot vacuum (FastMCP 3.1 / SEP-1577).

Uses ctx.sample() correctly: passes a text prompt to the LLM client,
which then calls back into our registered MCP tools (dreame_tool) as needed.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastmcp import Context
from pydantic import Field

from .portmanteau import fetch_status_data
from .state import _state

logger = logging.getLogger("dreame-mcp.agentic")


async def dreame_agentic_workflow(
    goal: Annotated[
        str, Field(description="Natural language goal, e.g. 'check battery and start cleaning if above 20%'.")
    ],
    ctx: Annotated[Context, Field(description="FastMCP sampling context (auto-injected).")],
) -> str:
    """Achieve a high-level Dreame robot vacuum goal via LLM planning (SEP-1577 sampling).

    The LLM client (Claude Desktop / cursor) receives the goal + status snapshot
    and may call back into dreame_tool via the MCP connection to gather status,
    map, or issue control commands.

    ## Return Format
    Markdown summary of the planned steps and outcome, or "Workflow failed: <err>"
    when sampling is unavailable.

    ## Examples
    dreame_agentic_workflow(goal="check battery and start cleaning if above 20%")
    """
    # Build a concise status snapshot to give the planner context
    try:
        status_result = await fetch_status_data(_state.get("client"))
        status_summary = (
            f"battery={status_result.get('battery', '?')}%, "
            f"state={status_result.get('state', '?')}, "
            f"charging={status_result.get('is_charging', '?')}"
        )
    except Exception:
        status_summary = "status unavailable"

    prompt = (
        f"Current robot status: {status_summary}\n\n"
        f"Goal: {goal}\n\n"
        "Available MCP tools (call via dreame_tool):\n"
        "  dreame_tool(operation='status')      — get full status\n"
        "  dreame_tool(operation='map')         — get LIDAR map\n"
        "  dreame_tool(operation='start_clean') — start cleaning\n"
        "  dreame_tool(operation='stop')        — stop\n"
        "  dreame_tool(operation='pause')       — pause\n"
        "  dreame_tool(operation='go_home')     — return to dock\n"
        "  dreame_tool(operation='find_robot')  — play locator sound\n"
        "  dreame_tool(operation='battery')     — battery % only\n\n"
        "Plan and execute steps to achieve the goal. "
        "Summarize what you did and the outcome."
    )

    try:
        result = await ctx.sample(prompt)
        text = getattr(result, "text", None)
        return text or str(result)
    except Exception as e:
        logger.exception("Agentic workflow sampling failed")
        return f"Workflow failed: {e}"
