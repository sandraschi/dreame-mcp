# dreame-operator — Dreame Robot Vacuum Operations

## What this server does

Control a Dreame D20 Pro Plus robot vacuum through the DreameHome cloud API
(and optionally local miio in hybrid mode). Provides device status telemetry,
LIDAR map retrieval with room/path/zone data, cleaning controls, and an
agentic workflow that plans multi-step cleaning goals via LLM sampling.

## Tools

### `dreame_tool(operation=...)` — portmanteau
- `status` — full telemetry: battery, state, cleaned area, cleaning time, charging, fan speed
- `battery` — battery percentage only
- `map` — LIDAR map summary: rooms, robot position, movement trail, restricted zones
- `start_clean`, `stop`, `pause`, `go_home`, `find_robot` — navigation & control

### `dreame_help(category=...)`
Multi-level help. Categories: `status`, `map`, `control`, `connection`, `agentic`.

### `dreame_agentic_workflow(goal=...)`
LLM plans and executes multi-step goals via MCP sampling (e.g. "check battery
and start cleaning if above 20%"). The planner calls back into `dreame_tool`.

### `dreame_shutdown()`
Gracefully disconnects the client and stops the server.

## Best practices

1. Start with `dreame_tool(operation='status')` to verify connectivity before control ops.
2. Use `dreame_agentic_workflow` for compound goals; use `dreame_tool` directly for single commands.
3. `map` may take up to 60s on slow cloud links — the server serializes map fetches.
4. Control commands execute through the cloud when no local IP is set; hybrid mode
   (DREAME_IP + DREAME_USER/PASSWORD) gives fast local control plus cloud maps.

## Configuration

- `DREAME_USER` / `DREAME_PASSWORD` / `DREAME_COUNTRY` — DreameHome cloud credentials (required for maps)
- `DREAME_DID` — optional device id (auto-discovered when a single device)
- `DREAME_IP` / `DREAME_TOKEN` — optional local miio (null-token trick when token blank)
- `DREAME_MCP_PORT` — backend port (default 10894)
- `DREAME_REF_PATH` — path to the Tasshack dreame-vacuum reference clone

## REST endpoints

`GET /api/v1/health`, `GET /api/v1/status`, `GET /api/v1/map`,
`GET /api/v1/map/png` (PNG download), `POST /api/v1/control/{cmd}`,
`GET /api/v1/diagnostics`, `POST /api/v1/shutdown`, `GET /api/skills`,
`GET /api/llm/providers`, `POST /api/llm/chat`.
