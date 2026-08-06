# MCP Tools

## `dreame_tool(operation=...)` — portmanteau

Unified control + telemetry. All operations return Markdown for LLM context.

| operation | Description |
|---|---|
| `status` | Full telemetry: battery, state, cleaned area, cleaning time, charging, fan speed |
| `battery` | Battery percentage only |
| `map` | LIDAR map summary: rooms, robot position, movement trail, restricted zones |
| `start_clean` | Start cleaning |
| `stop` | Stop cleaning |
| `pause` | Pause cleaning |
| `go_home` | Return to dock |
| `find_robot` | Play the locator sound |

## `dreame_help(category=...)`

Multi-level help. Categories: `status`, `map`, `control`, `connection`, `agentic`.

## `dreame_agentic_workflow(goal=...)`

LLM plans and executes multi-step goals via MCP sampling
(e.g. "check battery and start cleaning if above 20%"). The planner calls back
into `dreame_tool` as needed.

## `dreame_shutdown()`

Gracefully disconnects the Dreame client and stops the server.

## Prompts

- `dreame_quick_start` — setup and connect instructions
- `dreame_diagnostics` — diagnostic checklist

## REST endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/health` | Liveness probe |
| `GET /api/v1/status` | Robot status JSON |
| `GET /api/v1/map` | Map JSON (rooms, path, zones, image) |
| `GET /api/v1/map/png` | Rendered floor plan PNG |
| `GET /api/v1/map/pgm` / `yaml` | ROS2 nav2_map_server pair |
| `POST /api/v1/control/{cmd}` | start_clean/stop/pause/go_home/find_robot |
| `GET /api/v1/diagnostics` | Tool list, system info (CUA smoke testing) |
| `POST /api/v1/shutdown` | Graceful shutdown |
| `GET /api/skills` | Skill list (`skill://` resources) |
| `GET /api/logs` (+ export) | Activity log ring buffer |
| `GET /api/llm/providers` | Ollama model discovery |
| `POST /api/llm/chat` | Ollama chat completion |
