# Dreame D20 Pro Plus MCP Server

[![FastMCP Version](https://img.shields.io/badge/FastMCP-3.2.0-blue?style=flat-square&logo=python&logoColor=white)](https://github.com/sandraschi/fastmcp) [![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff) [![Linted with Biome](https://img.shields.io/badge/Linted_with-Biome-60a5fa?style=flat-square&logo=biome&logoColor=white)](https://biomejs.dev/) [![Built with Just](https://img.shields.io/badge/Built_with-Just-000000?style=flat-square&logo=gnu-bash&logoColor=white)](https://github.com/casey/just)

FastMCP 3.2.0 MCP server and webapp for the **Dreame D20 Pro Plus** robot vacuum.
Uses the **DreameHome cloud API**  no local token or miio required.
Protocol layer extracted from [Tasshack/dreame-vacuum](https://github.com/Tasshack/dreame-vacuum).

## Features

- **MCP tools**: `dreame(operation=...)`  status, map, start_clean, stop, pause, go_home, find_robot, battery
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
| `DREAME_USER` |  | DreameHome email or phone |
| `DREAME_PASSWORD` |  | DreameHome password |
| `DREAME_COUNTRY` |  | Cloud region, default `eu` |
| `DREAME_DID` |  | Device ID, auto-discovered if single device |
| `DREAME_AUTH_KEY` |  | Refresh token from previous login (speeds up startup) |
| `DREAME_REF_PATH` |  | Path to tasshack ref clone (default: `D:/Dev/repos/tasshack_dreame_vacuum_ref`) |
| `DREAME_MCP_PORT` |  | Backend port (default: `10894`) |
| `DREAME_IP` / `DREAME_TOKEN` |  | Local miio (null token if token empty); hybrid with cloud for maps |

## Development and tests

- **Python** (repo root): `uv run ruff check src tests`, `uv run pytest` (CI sets `PYTHONPATH=src`; on Windows: `$env:PYTHONPATH = 'src'; uv run pytest tests`).
- **MCP tool `dreame(operation=...)`** returns **Markdown** for LLM context. For **structured dicts** (same shapes as the REST handlers), import `fetch_status_data`, `fetch_map_data`, and `execute_control_data` from `dreame_mcp.portmanteau` (see `tests/test_map.py`).
- **Live tests** (real robot + cloud): `DREAME_LIVE=1 uv run pytest tests --live` or `--live` flag.
- **Webapp** (`webapp/`): `npm ci` then `npm run biome:ci` and `npm run build`.

## Connection Modes

This server supports three operational modes depending on your `.env` configuration:

| Mode | Credentials | Commands | Lidar Map | Notes |
| :--- | :--- | :---: | :---: | :--- |
| **Local** | `DREAME_IP` | ⚡ Local | ❌ No | Uses the **Null Token trick** (`000...000`) |
| **Cloud** | `USER` + `PWD` | ☁️ Cloud | ✅ Yes | Subject to cloud latency and API rate limits |
| **Hybrid** | **Both** | ⚡ **Local** | ✅ **Yes** | **Recommended**: Fast control + Full visual map |

### The "Null Token" Trick (Bypass)

For users avoiding the DreameHome cloud for controls, you do not need to extract a secret 32-character token. By providing only the `DREAME_IP`, the backend automatically uses a **Null Token** (`32 zeros`). This works on many bridged or circumvention-ready firmwares (like those used with the Tasshack protocol).

## Setup

1. **Configure credentials**: Copy `.env.example` to `.env` and fill in your details.
   ```powershell
   # Typical Hybrid Setup (.env)
   DREAME_IP=192.168.0.178
   DREAME_USER=your@email.com
   DREAME_PASSWORD=yourpassword
   ```

2. **Start the system**:
   ```powershell
   # Start backend + webapp together
   .\webapp\start.ps1
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
- **Fields:** `image` (base64 PNG when render works), `raw_b64` (always present when fetch succeeds  use for custom decoders or **robotics-mcp / yahboom-mcp** pipelines), optional `map_data` / `render_error`.

See **[docs/MAP_AND_ROBOTICS.md](docs/MAP_AND_ROBOTICS.md)** for fleet integration, CORS, and operational notes.

### Map rendering (PNG)

Rendered PNG requires the Tasshack dependency chain: `py-mini-racer`, `numpy`, `Pillow`, `cryptography`, etc.
If `dreame(operation='map')` returns `render_error`, decoding deps may be missing; **`raw_b64`** is still the portable fallback.

## Troubleshooting: `Unable to discover the device` / status 502

`GET /api/v1/health` includes **`local_miot`**: `true` only after a successful UDP miio handshake to `DREAME_IP` (port 54321). If you see **`Unable to discover the device` `192.168.x.x`** in logs or **`local_miot: false`**, the robot did not answer the standard miio discovery on the LAN. Typical causes: **DreameHome-only firmware** (no or limited LAN miio), **wrong IP**, **null token not accepted** (add a real **`DREAME_TOKEN`**), or **cloud login failed** (fix **`DREAME_USER` / `DREAME_PASSWORD` / `DREAME_COUNTRY`**, captcha, 2FA) so you get **`DREAME_DID`** and maps. Set **`DREAME_DID`** manually in `.env` when you know it from the app or cloud.

## Docs

- [Map and fleet robotics](docs/MAP_AND_ROBOTICS.md)  HTTP/MCP consumption, miIO vs cloud, yahboom / robotics integration
- [PRD](docs/PRD.md)  product context, ports, **5 Map API contract**
- [Token and Home Assistant](docs/TOKEN_AND_HOME_ASSISTANT.md)  historical miIO reference (v0.2+ uses cloud)


## 🛡️ Industrial Quality Stack

This project adheres to **SOTA 14.1** industrial standards for high-fidelity agentic orchestration:

- **Python (Core)**: [Ruff](https://astral.sh/ruff) for linting and formatting. Zero-tolerance for `print` statements in core handlers (`T201`).
- **Webapp (UI)**: [Biome](https://biomejs.dev/) for sub-millisecond linting. Strict `noConsoleLog` enforcement.
- **Protocol Compliance**: Hardened `stdout/stderr` isolation to ensure crash-resistant JSON-RPC communication.
- **Automation**: [Justfile](./justfile) recipes for all fleet operations (`just lint`, `just fix`, `just dev`).
- **Security**: Automated audits via `bandit` and `safety`.
