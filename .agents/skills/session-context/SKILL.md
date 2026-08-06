---
name: session-context
description: Lightweight Dreame robot vacuum session start prompt
---

## Session Context (Dreame-MCP)

You have access to Dreame robot vacuum control via DreameHome cloud: device status, LIDAR map, and cleaning controls.

**Before starting work:**
1. Check device status: `dreame_tool(operation="status")`
2. View current map: `dreame_tool(operation="map")`
3. Verify connectivity: `dreame_help(category="connection")`

**At end of work:**
- If a cleaning task was issued, confirm completion: `dreame_tool(operation="status")`
- No other cleanup needed (read-only device queries are safe)
