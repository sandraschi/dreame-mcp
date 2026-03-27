# Map data and fleet robotics (yahboom-mcp, robotics-mcp)

This document describes how **floor map / LIDAR-related data** is obtained in dreame-mcp and how other automation stacks can consume it **without miIO**.

## Does the map require miIO?

**No.** Map retrieval uses the **DreameHome cloud** path: authenticated session, device properties (including live `OBJECT_NAME`), then file fetch and optional decode/render via the Tasshack map layer loaded from `DREAME_REF_PATH`.

Local **miIO** (`DREAME_IP` + token) is a **different** integration path used by some Xiaomi-ecosystem vacuums. On many DreameHome-only firmwares (including typical D20 Pro Plus setups), local miIO is unavailable or incomplete. This server’s primary path is cloud-based.

## HTTP API (stable for other repos)

With the backend running (default **10894**):

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/health` | `connected`, `did`, sanity check before map |
| `GET /api/v1/map` | Same payload as `dreame(operation='map')` — JSON |

### Response pattern (important for consumers)

**Single JSON document — no multipart, no trailing binary stream.**  
FastAPI returns one `application/json` body. Map payloads are **embedded as base64 strings** inside that JSON (standard pattern for “binary in JSON” APIs).

- **`raw_b64`** — Always present on **success**: base64 encoding of the **raw map file bytes** from Dreame cloud (the same blob the Tasshack stack would decode). Consumers that implement their own decoder or only need the archive should use this.
- **`image`** — Optional: base64-encoded **PNG** bytes (no `data:image/png;base64,` prefix — just the base64 string). Present when the Tasshack map manager decoded and rendered successfully.
- **`map_data`** — Optional small object when decode succeeded: e.g. `rooms` (count), `robot_position` / `charger_position` as `{ "x", "y" }`.
- **`raw_bytes`** — Integer: length of the decoded raw file (same as `len(base64.b64decode(raw_b64))` when valid).
- **`render_error`** — Optional string if decode/render failed; **`raw_b64` is still present** so pipelines can fall back to raw-only.

**Errors:** HTTP **502** with body `{"detail":"<message>"}` when `success` would be false (e.g. not connected, no map file from cloud). This is **not** the same shape as the success object — clients should check HTTP status first, then parse `detail` on failure.

**Stub mode** (no `DREAME_USER` / `DREAME_PASSWORD`): the tool may return `success: true` with a stub `message` and empty `map` — not real map bytes; treat as misconfiguration for production consumers.

## Using this from robotics-mcp or yahboom-mcp

1. **Direct HTTP** — From the same machine or LAN, call `http://127.0.0.1:10894/api/v1/map` (or host + port you configured). Parse JSON; base64-decode `raw_b64` or use `image` as a data URL / save to PNG.
2. **MCP** — Use the `dreame` tool with `operation='map'` from a client that has dreame-mcp connected; same fields as REST.
3. **Webapp proxy** — The Vite dev server proxies `/api` to the backend; for a **full URL** from another process, prefer the backend URL above unless you inject `VITE_DREAME_MAP_URL` / `VITE_DREAME_API_BASE` for a known origin.

**CORS:** The FastAPI app allows broad CORS for browser use; for server-to-server calls, plain HTTP is enough.

## Tasshack dependency

Protocol and map logic are loaded at runtime from a local clone of [Tasshack/dreame-vacuum](https://github.com/Tasshack/dreame-vacuum) (default path `D:/Dev/repos/tasshack_dreame_vacuum_ref`, overridable with `DREAME_REF_PATH`). dreame-mcp does not vendor that code; it adapts it behind FastMCP and REST.

## Operational notes

- A **published map** on the robot (cleaning / mapping run) improves the chance that cloud `OBJECT_NAME` and file fetch succeed.
- Wrong **`DREAME_COUNTRY`** or **`DREAME_DID`** can yield empty or failed fetches.
- If rendering fails, **`raw_b64`** is still the main artifact for robotics pipelines that implement their own map handling.

See also: [README](../README.md) (environment variables), Help → **Connection methods** in the webapp, and [PRD](PRD.md) § fleet map source.
