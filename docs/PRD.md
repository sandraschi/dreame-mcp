# dreame-mcp — Product Requirements Document

**Version:** 0.2.0  
**Date:** 2026-03-17  
**Status:** Active development  
**Owner:** sandraschi

---

## 1. Purpose

Provide AI-accessible control and monitoring of the **Dreame D20 Pro Plus** robot vacuum
(`dreame.vacuum.r2566a`) via the Model Context Protocol (MCP), using the DreameHome cloud API.

The server exposes a portmanteau tool, agentic workflow, REST API, and SOTA React dashboard.
It serves as a **map source** for other fleet tools (yahboom-mcp, robotics-mcp) via
`GET /api/v1/map` — see §5 and repo `docs/MAP_AND_ROBOTICS.md`.

---

## 2. Context & constraints

| Item | Detail |
|------|--------|
| Device | Dreame D20 Pro Plus, model `dreame.vacuum.r2566a` |
| DID | 2045852486 |
| Cloud | DreameHome (Alibaba Cloud), EU region |
| Local API | **Disabled** by DreameHome firmware — no miio token available |
| Mi Home | Device not listed — migration impossible |
| HA integration | Tasshack EU auth broken (open bug since mid-2025) |
| Protocol source | Tasshack/dreame-vacuum ref clone (protocol.py + map.py) |
| Ports | Backend 10894, Frontend 10895 |

---

## 3. Goals

### 3.1 Must have (v0.2)
- [x] Cloud login via DreameHome credentials (email + password, EU region)
- [x] Status polling (battery, state, charging, cleaned area, time)
- [x] Vacuum control: start cleaning, stop, pause, return to dock, find robot
- [x] LIDAR map fetch from cloud (raw bytes)
- [x] Map decode + PNG render (via Tasshack map.py)
- [x] MCP portmanteau tool (`dreame`)
- [x] Agentic workflow with SEP-1577 sampling
- [x] REST API (health, status, map, control)
- [x] React dashboard (Dashboard, Status, Controls, Map, Tools, Settings, Help)
- [x] Fleet integration (starts/, FLEET_INDEX, WEBAPP_PORTS, project docs)

### 3.2 Should have (v0.3)
- [ ] Verify and fix `go_home` action mapping against actual device firmware
- [ ] Verify `pause`, `find_robot` action mappings
- [ ] Map polling / push updates via MQTT (currently optional/non-fatal)
- [ ] Auth token persistence — save `DREAME_AUTH_KEY` after login so restarts don't re-auth
- [ ] Consumable status (brush/filter wear %) — cloud API endpoint research needed
- [ ] Room-level cleaning (clean segment X) — requires map room ID extraction
- [ ] Zone cleaning — requires map coordinate system understanding

### 3.3 Nice to have (v1.0)
- [ ] Schedule management (read/write cleaning schedules)
- [ ] Map as image endpoint — serve rendered PNG directly at `/api/v1/map/image`
- [ ] Live robot position overlay on map (MQTT push position updates)
- [ ] Multi-robot support (fleet of Dreame vacuums)
- [x] HTTP map contract for fleet consumers (`GET /api/v1/map`, `docs/MAP_AND_ROBOTICS.md`) — cross-robot **consumption** documented; deeper **shared SLAM** integration still optional
- [ ] Glama.ai publication

---

## 4. Architecture

```
Claude Desktop / Cursor
    │  MCP SSE (stdio or http://localhost:10894/sse)
    ▼
dreame-mcp server (FastMCP 3.1)
    ├── dreame(operation)     ← portmanteau tool
    ├── dreame_help()
    └── dreame_agentic_workflow(goal)  ← ctx.sample() SEP-1577
         │
         ▼
    DreameHomeClient (client.py)
         ├── login()          ← DreameHome cloud auth (JWT)
         ├── get_status()     ← cloud properties
         ├── control(cmd)     ← actions over cloud
         └── get_map()        ← signed-URL get_file first; get_device_file fallback; decode+render
              │                   via DreameVacuumMapDecoder + DreameVacuumMapRenderer
              ▼
         tasshack_dreame_vacuum_ref/
              ├── protocol.py  ← DreameVacuumDreameHomeCloudProtocol
              └── map.py       ← DreameMapVacuumMapManager + DreameVacuumMapDecoder + DreameVacuumMapRenderer

React webapp (Vite, port 10895)
    └── proxies /api/* → http://localhost:10894
```

---

## 5. Map API contract (`GET /api/v1/map`)

Stable integration surface for **robotics-mcp**, **yahboom-mcp**, and other consumers.

| Aspect | Detail |
|--------|--------|
| Transport | Single **`application/json`** response body — **no** multipart, **no** trailing binary stream |
| Success shape | `success: true` plus inline base64 fields (see below) |
| Failure shape | HTTP **502**, body `{"detail": "<message>"}` (FastAPI) — not the success object |
| `raw_b64` | **Always on success** — base64 of raw Dreame cloud map file bytes (primary artifact for custom decoders / fleet pipelines) |
| `image` | Optional — base64 **image** (no `data:` prefix) when Tasshack decode + `DreameVacuumMapRenderer.render_map` succeed |
| `map_data` | Optional — `{ rooms, robot_position, charger_position }` when decode succeeds |
| `raw_bytes` | Integer — length of raw file |
| `render_error` | Optional — present if decode/render failed; `raw_b64` still returned on successful download |

**miIO not required** for map: see `docs/MAP_AND_ROBOTICS.md` (signed-URL download first, then optional Tasshack decode/render).

---

## 6. MiIO property/action IDs (verified from Tasshack types.py)

| Property | siid | piid | Notes |
|----------|------|------|-------|
| STATE | 2 | 1 | operating state enum |
| ERROR | 2 | 2 | error code |
| BATTERY_LEVEL | 3 | 1 | % |
| CHARGING_STATUS | 3 | 2 | 0=not charging, 1=charging, 2=charged |
| STATUS | 4 | 1 | detailed status |
| CLEANING_TIME | 4 | 2 | seconds |
| CLEANED_AREA | 4 | 3 | cm² |
| SUCTION_LEVEL | 4 | 4 | fan speed code |

| Action | siid | aiid | Status |
|--------|------|------|--------|
| start_clean (START) | 2 | 1 | ✅ confirmed |
| pause (PAUSE) | 2 | 2 | untested |
| go_home (CHARGE) | 3 | 1 | ✅ fixed — was wrong (2,4) |
| stop (STOP) | 4 | 2 | untested |
| find_robot (LOCATE) | 7 | 1 | untested |

## 7. What robot vacuums at this level do NOT expose

For reference — common questions:

- **Manual movement** (forward/back/strafe): No cloud API. Only available via local miio
  `remote_control` mode (requires local token — unavailable on DreameHome devices).
- **Goto position**: No. Requires local protocol + map coordinate translation.
- **Room-by-room cleaning**: Possible via `START_CUSTOM` (siid:4, aiid:1) with segment IDs,
  but requires parsing map data to get room IDs first.
- **Zone cleaning**: Same — needs map coordinate system, local or cloud map data.
- **Consumable wear %**: Available via cloud properties (brush/filter remaining hours),
  not yet implemented.
- **Schedules**: Read/write via cloud properties, not yet implemented.

---

## 8. Known issues

| Issue | Severity | Status |
|-------|----------|--------|
| go_home reliability | Medium | Verify on firmware; PRD action table uses Tasshack (3,1) for CHARGE |
| py-mini-racer Windows install | Low | Optional dep — map works without it (raw_b64) |
| MQTT occasionally fails to connect | Low | Non-fatal, polling works |
| Map decode untested against r2566a | Low | r2566a: signed-URL + decoder/renderer path confirmed in the field (2026) |
| Auth key not persisted across restarts | Low | Re-auths on every start |

---

## 9. Non-goals

- Local-only operation (DreameHome firmware prevents this)
- Replacing the DreameHome mobile app
- Supporting other Dreame models without testing
