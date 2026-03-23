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
| `DREAME_MCP_PORT` | — | Backend port (default: `10794`) |

## Setup

```powershell
# Set credentials (or use a .env file)
$env:DREAME_USER = "your@email.com"
$env:DREAME_PASSWORD = "yourpassword"
$env:DREAME_COUNTRY = "eu"

# Start backend
uv run python -m dreame_mcp --mode dual --port 10794

# Start webapp (separate terminal)
cd webapp
.\start.ps1
```

## MCP client config

```json
{
  "mcpServers": {
    "dreame": {
      "url": "http://localhost:10794/sse",
      "transport": "sse"
    }
  }
}
```

## Map rendering

Map rendering requires the full Tasshack dep chain: `py-mini-racer`, `numpy`, `Pillow`, `cryptography`.
If `dreame(operation='map')` returns `render_error`, the deps are missing.
The `raw_b64` field is always returned as fallback (raw map bytes for custom processing).

## Docs

- [Token and Home Assistant](docs/TOKEN_AND_HOME_ASSISTANT.md) — historical reference
