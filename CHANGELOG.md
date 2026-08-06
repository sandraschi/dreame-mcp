# Changelog

All notable changes to dreame-mcp are documented here.

---

## [Unreleased]

### Added — assfix 2026-08-06 (SOTA pass)

- **Ports corrected fleet-wide**: backend default `10794` → `10894` (server.py,
  justfile `start-hybrid`, prompts); `backend.rs` `BACKEND_PORT` `10700` → `10894`;
  Tauri CSP `connect-src` → `127.0.0.1:10894`; `cua-nsis-config.json` backend port +
  `nav_routes`; `Tools.tsx` SSE URL `10794` → `10894`.
- **`GET /api/v1/diagnostics`** endpoint (tools, system info) for CUA-NSIS smoke testing.
- **`GET /api/skills`** + `skill://dreame-operator/SKILL.md` resource (skill-first chat).
- **`dreame_shutdown`** MCP tool + `POST /api/v1/shutdown` (graceful uvicorn exit).
- **Docstring SOTA** on all four tools: `## Return Format`, `## Examples`,
  `Annotated+Field` params, `Literal` operation enum, tool annotations.
- **Webapp**: `API_BASE` → backend port `10894` (fixes prod/Tauri fetch), Tauri
  `backend-status` listener + exponential-backoff health poll + Restart Backend
  button + `data-testid` KPIs, `useZoom()` Ctrl+Scroll zoom, 4th chat personality
  (Custom), 6 example prompts, LLM status dot.
- **Native pipeline**: `run_server.py` (dual transport) + `dreame-mcp-backend.spec`
  (PyInstaller) so `just build-native` can produce the embedded backend;
  multi-layer `free_port()` + TCP health poll in `backend.rs`.
- **Tooling**: `T20` in ruff select + per-file-ignores; `pyright` + `pre-commit`
  dev deps; `.pre-commit-config.yaml` + `scripts/pre-commit-biome.ps1`;
  `just serve` / `just test`; CI gains pyright + format steps and push/PR triggers.
- **Repo hygiene**: `.gitattributes` (eol=lf), `.gitignore` (`reports/`, `*.mcpb`,
  native artifacts; `uv.lock` un-ignored), `.mcpbignore` (webapp/, scratch/, *.bak),
  `.windsurfrules`, `.github/copilot-instructions.md`, `.claude-plugin/` + hooks,
  `.opencode/skills/session-context`.
- **Docs**: `docs/CONFIGURATION.md`, `DEVELOPMENT.md`, `TOOLS.md`,
  `TROUBLESHOOTING.md`, `ONBOARDING.md`; README/llms-full.txt synced.
- **Fixes**: agentic workflow now reads real status (dict-vs-str bug); auth key no
  longer logged at INFO; stdio transport uses `run_stdio_async()` (old
  `fastmcp.cli.run_stdio` import was broken on 3.4.x); pyright clean (13 errors
  fixed); biome clean (52 format/lint errors fixed).

### Fixed — LIDAR map (download + image) + local/hybrid (Tasshack)

- **Signed-URL first** on `protocol.cloud` or unified protocol (`get_interim_file_url` / `get_file` / `get_file_url`); `get_device_file` is fallback (limited attempts); then **siid=23, piid=1** (raw map property) and a final `get_file_url`+`get_file` pass. **`MAP_FETCH_TIMEOUT` 60s**; map fetches are **serialized** with a lock; **`DreameVacuumMapDecoder` + `DreameVacuumMapRenderer`**, with rich **`map_data`** (rooms, path, areas, dimensions).
- **Bootstrap**: Tasshack package stubs set `__path__` so `dreame.types` / `map` import.
- **Hybrid client**: `DreameVacuumProtocol` (local + cloud), `_safe_call` forwards file methods to `protocol.cloud` when needed; `control()` uses Tasshack **`action`**, cloud device pick uses **`DREAME_DID`** / **`DREAME_IP`**, **`disconnect()`** clears protocol and map state.
- **Portmanteau / tests / lint**: as before; `dreame_tool` Markdown, `fetch_*` dicts; Ruff + Biome + pytest; ASCII markdown in tool strings where applicable.

### Fixed — LIDAR map download hang (critical)

- **`asyncio.wait_for()` on all `run_in_executor` calls**: `get_map()` (60s), `get_status()` / `control()` (35s), `connect()` (30s). Previously, any cloud timeout cascaded into indefinite blocking of the REST endpoint and MCP tool.
- **Fail-fast file-type loop**: Map fetch now bails after 2 cloud failures instead of exhausting all 4 type variants (was up to 60s cumulative per attempt).
- **Object name for map**: `get_properties` for `OBJECT_NAME` (6.3) when the API returns data; otherwise `protocol.object_name`.
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
- README — map section (signed-URL + decoder/renderer, dashboard Map page), ports **10894**, links to PRD/MAP_AND_ROBOTICS.
- **docs/MAP_AND_ROBOTICS.md** — end-to-end pipeline section.
- **docs/PRD.md** — architecture diagram + map table for decode/render; known-issue row for r2566a map.
- **Webapp:** Help — new **Map API** tab; Connection methods icon; troubleshooting map line; Settings aligned with cloud env vars and `VITE_*` overrides. **webapp/README** — dreame dashboard overview and proxy note.

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
