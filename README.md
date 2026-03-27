# Dreame D20 Pro Plus MCP Server

FastMCP 3.1 MCP server and webapp for the **Dreame D20 Pro Plus** robot vacuum.
Uses the **DreameHome cloud API** — no local token or miio required.
Protocol layer extracted from [Tasshack/dreame-vacuum](https://github.com/Tasshack/dreame-vacuum).

## Features

- **MCP tools**: `dreame(operation=...)` — status, map, start_clean, stop, pause, go_home, find_robot, battery
- **MCP tools**: `dreame_help(category)`, `dreame_agentic_workflow(goal)` with SEP-1577 sampling
- **Prompts**: `dreame_quick_start`, `dreame_diagnostics`
- **Skills**: `skills/dreame-operator.md`
- **REST API**: GET /api/v1/health, /api/v1/status, /api/v1/map; POST /api/v1/control/{cmd}
- **Webapp**: Dashboard, LIDAR Map, Status, Controls, Settings, Help, MCP Tools

## Ports

- Backend: **10894** (REST + MCP SSE)
- Dashboard: **10895** (Vite dev server)

## Prerequisites

1. Clone **this** repo and enter it:
   ```powershell
   git clone https://github.com/sandraschi/dreame-mcp.git
   Set-Location dreame-mcp
   ```

2. Clone the Tasshack dreame-vacuum reference repo (protocol + map layer). Default ref path is `D:/Dev/repos/tasshack_dreame_vacuum_ref`:
   ```powershell
   Set-Location D:\Dev\repos
   git clone https://github.com/Tasshack/dreame-vacuum tasshack_dreame_vacuum_ref
   Set-Location dreame-mcp
   ```
   (Adjust paths if your dev folder is not `D:\Dev\repos`; set `DREAME_REF_PATH` accordingly.)

3. Install Python deps from the **dreame-mcp** repository root:
   ```powershell
   uv sync
   ```

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `DREAME_USER` | ✅ | DreameHome email or phone |
| `DREAME_PASSWORD` | ✅ | DreameHome password |
| `DREAME_COUNTRY` | — | Cloud region, default `eu` |
| `DREAME_DID` | — | Device ID, auto-discovered if single device |
| `DREAME_AUTH_KEY` | — | Refresh token from previous login (speeds up startup) |
| `DREAME_REF_PATH` | — | Path to tasshack ref clone (default: `D:/Dev/repos/tasshack_dreame_vacuum_ref`) |
| `DREAME_MCP_PORT` | — | Backend port (default: `10894`) |

## Setup

```powershell
# Set credentials (or use a .env file)
$env:DREAME_USER = "your@email.com"
$env:DREAME_PASSWORD = "yourpassword"
$env:DREAME_COUNTRY = "eu"

# Start backend
uv run python -m dreame_mcp --mode dual --port 10894

# Start webapp (separate terminal)
cd webapp
.\start.ps1
```

## MCP client config

```json
{
  "mcpServers": {
    "dreame": {
      "url": "http://localhost:10894/sse",
      "transport": "sse"
    }
  }
}
```

## Map (LIDAR / floor plan)

**Map data does not require miIO** on this server: it uses DreameHome cloud + the Tasshack map layer from `DREAME_REF_PATH`. Local miIO is optional and often unavailable on DreameHome-only firmware.

- **REST:** `GET http://localhost:10894/api/v1/map` (same JSON as MCP `dreame(operation='map')`).
- **Fields:** `image` (base64 PNG when render works), `raw_b64` (always present when fetch succeeds — use for custom decoders or **robotics-mcp / yahboom-mcp** pipelines), optional `map_data` / `render_error`.

See **[docs/MAP_AND_ROBOTICS.md](docs/MAP_AND_ROBOTICS.md)** for fleet integration, CORS, and operational notes.

### Map rendering (PNG)

Rendered PNG requires the Tasshack dependency chain: `py-mini-racer`, `numpy`, `Pillow`, `cryptography`, etc.
If `dreame(operation='map')` returns `render_error`, decoding deps may be missing; **`raw_b64`** is still the portable fallback.

## Docs

- [Map and fleet robotics](docs/MAP_AND_ROBOTICS.md) — HTTP/MCP consumption, miIO vs cloud, yahboom / robotics integration
- [PRD](docs/PRD.md) — product context, ports, **§5 Map API contract**
- [Token and Home Assistant](docs/TOKEN_AND_HOME_ASSISTANT.md) — historical miIO reference (v0.2+ uses cloud)
