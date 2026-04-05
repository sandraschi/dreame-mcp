# Changelog

All notable changes to dreame-mcp are documented here.

---

## [Unreleased]

### Fixed — LIDAR map download hang (critical)

- **`asyncio.wait_for()` on all `run_in_executor` calls**: `get_map()` (45s), `get_status()` / `control()` (35s), `connect()` (30s). Previously, any cloud timeout cascaded into indefinite blocking of the REST endpoint and MCP tool.
- **Fail-fast file-type loop**: Map fetch now bails after 2 cloud failures instead of exhausting all 4 type variants (was up to 60s cumulative per attempt).
- **Removed broken `get_properties(["6.3"])` live object_name lookup**: Tasshack `get_properties()` returns a different response shape than expected; the code always fell through silently. Now uses `protocol.object_name` directly.
- **Thread pool increased from 2 to 4**: Prevents deadlock when concurrent map + status calls both block on cloud I/O.
- **Frontend `AbortController` + timeout**: `api.ts` now aborts all fetch calls after 15s (50s for map), preventing infinite spinner in the webapp.
- **Map page timeout UX**: `Map.tsx` shows distinct timeout indicator (blue clock icon) with retry guidance instead of generic error.

### Fixed — Secondary

- Version mismatch: `__init__.py` synced to `0.2.0` (was stale `0.1.0`).
- `__main__.py` docstring port corrected: `10794` → `10894`.
- Removed unused `React` import in `Map.tsx` (React 19 automatic JSX).

### Changed

- FastMCP dependency bumped to `>=3.2.0`.
- Added Ruff config (`pyproject.toml`): 120-char lines, py312 target.

### Docs

- Added `docs/MAP_AND_ROBOTICS.md` (map vs miIO, `/api/v1/map` JSON contract, fleet use with robotics-mcp / yahboom-mcp).
- `docs/PRD.md` — §5 Map API contract; renumbered sections; fleet map purpose clarified.
- `docs/TOKEN_AND_HOME_ASSISTANT.md` — v0.2+ cloud-first note; miIO doc marked historical.
- README — map section, ports **10894**, links to PRD/MAP_AND_ROBOTICS.
- **Webapp:** Help — new **Map API** tab; Connection methods icon; troubleshooting map line; Settings aligned with cloud env vars and `VITE_*` overrides.

### Central docs mirror

- `mcp-central-docs`: integrations index, `projects/dreame-mcp/README.md`, `FLEET_INDEX.md` — Dreame ports and descriptions (10894/10895, cloud, map API).

## [0.2.0] — 2026-03-17

### Changed — DreameHome cloud migration (breaking)

The D20 Pro Plus (`dreame.vacuum.r2566a`) is a DreameHome-only device:
- No local miio token available
- Not supported by Mi Home
- HA Tasshack EU auth broken (known open bug)

The backend has been completely rewritten to talk directly to the **DreameHome cloud API**
using the protocol layer from [Tasshack/dreame-vacuum](https://github.com/Tasshack/dreame-vacuum)
(ref clone at `D:/Dev/repos/tasshack_dreame_vacuum_ref`).

#### Removed
- `python-miio` dependency — local token/miio control gone
- `DREAME_IP`, `DREAME_TOKEN`, `DREAME_MAP_URL` env vars

#### Added
- `DreameHomeClient` (`src/dreame_mcp/client.py`) — async wrapper around Tasshack's
  `DreameVacuumDreameHomeCloudProtocol`, with auto-discovery of device DID
- Cloud env vars: `DREAME_USER`, `DREAME_PASSWORD`, `DREAME_COUNTRY`, `DREAME_DID`,
  `DREAME_AUTH_KEY`, `DREAME_REF_PATH`
- MQTT push updates via Tasshack protocol (non-fatal if unavailable)
- LIDAR map decode + PNG render via Tasshack `map.py` (requires `py-mini-racer`, `numpy`,
  `Pillow`, `cryptography`); `raw_b64` fallback always returned
- `DREAME_MCP_PORT` env var (default 10894)
- `starts/dreame-start.bat` fleet shortcut

#### Fixed
- `ctx.sample()` in `agentic.py` — was passing invalid `tools=` kwarg (FastMCP 3.x incompatibility)
- `vite.config.ts` dev server port (was 10895→10795 off-by-100 typo, now correct 10895)
- `ErrorBoundary.tsx` missing default export
- `Vacuum` lucide-react icon (doesn't exist in installed version) → replaced with `Bot`
- All `webapp/start.ps1` issues: PS 5.1 `?.` syntax, `$var:` colon parse error, PATH not
  refreshed from bat context, `npm ci` vs stale lock file, `Start-Process -WindowStyle Hidden`
  conflicting with stdout redirect

#### Known issues
- `go_home` (return to dock) — cloud action mapping may need verification against actual
  device firmware; start_clean confirmed working

---

## [0.1.0] — 2026-03-07

### Initial release

- FastMCP 3.1 MCP server for Dreame D20 Pro vacuum
- `dreame(operation=...)` portmanteau tool (status, map, start_clean, stop, pause,
  go_home, find_robot, battery)
- `dreame_help(category)`, `dreame_agentic_workflow(goal)` tools
- Prompts: `dreame_quick_start`, `dreame_diagnostics`
- Skill: `skills/dreame-operator.md`
- REST API: health, status, map, control
- React/Vite/Tailwind SOTA webapp on ports 10894/10895
- python-miio backend (stub mode without token)
