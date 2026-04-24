# Dreame D20 Pro Plus Operator Skill

## Scope
Operate the **Dreame D20 Pro Plus** robot vacuum (`dreame.vacuum.r2566a`) via the
dreame-mcp server (FastMCP 3.1, DreameHome cloud API). Uses the portmanteau tool
`dreame(operation=...)` and the agentic workflow for high-level goals.

No local token or miio required — all communication goes via the DreameHome cloud.

## Device facts
- Model: dreame.vacuum.r2566a
- DID: 2045852486
- Navigation: LDS LiDAR (Pathfinder)
- Suction: 13,000 Pa Vormax
- Brush: HyperStream DuoBrush (anti-tangle, no hair wrapping)
- Mop: plate mop, 350ml water tank, 32 moisture levels
- Auto-empty: 5L bag station, ~150 days capacity
- App: DreameHome (EU region, Alibaba Cloud)

## Tools

- **dreame(operation, param1, param2, payload)** — Single operation:
  - `status` — battery %, state, charging, cleaned area (m²), time (s)
  - `battery` — battery % only
  - `map` — LIDAR map: JSON with `raw_b64` (on successful cloud download) + optional `image` (base64 render from Tasshack decoder + `DreameVacuumMapRenderer`). Same as `GET /api/v1/map`. See `docs/MAP_AND_ROBOTICS.md`.
  - `start_clean` — start full clean ✅ confirmed
  - `stop` — stop cleaning
  - `pause` — pause cleaning
  - `go_home` — return to dock ⚠️ not working (action ID needs verification)
  - `find_robot` — play locator sound

- **dreame_help(category, topic)** — Drill-down help:
  - categories: status, map, control, connection, agentic

- **dreame_agentic_workflow(goal)** — High-level goal; LLM plans and executes
  sub-steps using dreame() calls via SEP-1577 sampling.

## Prompts
- **dreame_quick_start()** — Setup, env vars, ref clone, MCP client config.
- **dreame_diagnostics()** — Diagnostic checklist.

## Operator rules

1. Always call `dreame(operation='status')` before starting a clean to verify battery > 20%.
2. Do NOT attempt `go_home` — it is currently broken. Tell the user to dock via the DreameHome app.
3. Prefer `dreame_agentic_workflow` for multi-step goals (e.g. "clean then dock").
4. Map **download** uses DreameHome (signed-URL path first). MQTT helps live updates but is not strictly required for a one-off map fetch if the cloud can resolve the file.
5. The MCP server runs in stub mode if `DREAME_USER`/`DREAME_PASSWORD` are not set — all
   operations return fake data. Check health endpoint first.
6. Map rendering requires `py-mini-racer` + `numpy` + `Pillow`. If unavailable, `raw_b64` is
   returned instead of a rendered PNG.

## Known issues
- `go_home` returns success but robot does not dock — aiid mapping needs investigation
- Map decode/render: signed-URL + Tasshack decoder path verified for r2566a; if only `raw_b64` appears, check `render_error` and Python deps
- Auth key not persisted — server re-auths on every restart (adds ~3s to startup)
