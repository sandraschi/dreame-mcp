"""Agentic workflow for Dreame robot vacuum (FastMCP 3.1 / SEP-1577).

Uses ctx.sample() correctly: passes a text prompt to the LLM client,
which then calls back into our registered MCP tools (dreame_tool) as needed.
"""

from __future__ import annotations

import logging

from fastmcp import Context

from .portmanteau import dreame_tool

logger = logging.getLogger("dreame-mcp.agentic")


async def dreame_agentic_workflow(goal: str, ctx: Context) -> str:
    """Achieve a high-level Dreame robot vacuum goal via LLM planning (SEP-1577 sampling).

    The LLM client (Claude Desktop / cursor) receives the goal + system prompt and
    may call back into dreame_tool via the MCP connection to gather status, map, or
    issue control commands.

    Args:
        goal: Natural language goal, e.g. "check battery and start cleaning if above 20%"

    Returns:
        LLM summary of actions taken.
    """
    # Build a concise status snapshot to give the planner context
    try:
        status_result = await dreame_tool(ctx=ctx, operation="status")
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
        "  dreame(operation='status')      — get full status\n"
        "  dreame(operation='map')         — get LIDAR map\n"
        "  dreame(operation='start_clean') — start cleaning\n"
        "  dreame(operation='stop')        — stop\n"
        "  dreame(operation='pause')       — pause\n"
        "  dreame(operation='go_home')     — return to dock\n"
        "  dreame(operation='find_robot')  — play locator sound\n"
        "  dreame(operation='battery')     — battery % only\n\n"
        "Plan and execute steps to achieve the goal. "
        "Summarize what you did and the outcome."
    )

    try:
        result = await ctx.sample(prompt)
        return result.text if hasattr(result, "text") else str(result)
    except Exception as e:
        logger.exception("Agentic workflow sampling failed")
        return f"Workflow failed: {e}"
