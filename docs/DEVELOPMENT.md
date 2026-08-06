# Development

## Stack

- Python 3.12+, FastMCP 3.4.x, FastAPI + uvicorn, pydantic v2
- Webapp: React 19 + Vite 5 + Tailwind 3 + Biome + TypeScript

## Setup

```powershell
git clone https://github.com/sandraschi/dreame-mcp
cd dreame-mcp
just bootstrap          # uv sync + pre-commit install
copy .env.example .env  # fill in credentials
```

The Tasshack reference clone (`DREAME_REF_PATH`) must exist locally for the
protocol layer; without it the server runs in stub mode.

## Recipes

- `just serve` — fleet launcher (backend 10894 + webapp 10895)
- `just test` — mocked test suite
- `just lint` / `just fix` — ruff + biome
- `just e2e` — Playwright audit (webapp)
- `just mcpb-pack` — Claude Desktop bundle
- `just build-native` + `just cua-nsis-test` — Tauri NSIS build + smoke test
- `just cua-webapp-test` — pre-Tauri browser walk

## Tests

Mocked tests run headless (no robot, no cloud): `uv run pytest tests/ -q`.
Live tests need `DREAME_LIVE=1` and a real hoover — never run in CI.

## Verification gates (five-gate)

```powershell
uv run ruff check src tests
uv run ruff format src --check
uv run pyright src
uv run pytest tests/ -q
cd webapp; npm run biome:ci; npx tsc --noEmit
```

## Architecture

- `src/dreame_mcp/server.py` — FastAPI app, REST routes, MCP registration, entry point
- `src/dreame_mcp/client.py` — DreameHome cloud / local miio client (Tasshack protocol bootstrap)
- `src/dreame_mcp/portmanteau.py` — `dreame_tool(operation=...)` + structured fetchers
- `src/dreame_mcp/agentic.py` — LLM sampling workflow
- `src/dreame_mcp/map_export.py` — PNG/PGM/YAML map export (ROS2 formats)
- `src/dreame_mcp/activity_log.py` — in-memory log ring buffer + REST router
- `src/dreame_mcp/skills/` — skill:// resources
- `webapp/` — React dashboard
- `native/` — Tauri 2.0 shell (embedded PyInstaller backend)
