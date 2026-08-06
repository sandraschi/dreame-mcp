# Troubleshooting

## Backend won't start / port in use

Ports 10894 (backend) and 10895 (frontend) must be free. The fleet start script
kills port zombies automatically; if a manual kill is needed:

```powershell
Get-NetTCPConnection -LocalPort 10894 -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

## "Failed to fetch" in the webapp

- The webapp calls `http://127.0.0.1:10894` (backend) directly. In dev, Vite on
  10895 proxies `/api` too — the backend must be running on **10894**, not 10700.
- In the Tauri app, the WebView CSP allows `connect-src http://127.0.0.1:10894`
  — if the port changed, update `native/tauri.conf.json` CSP and
  `native/src/backend.rs` `BACKEND_PORT`.

## Robot shows "Not configured"

`DREAME_IP`/`DREAME_USER`/`DREAME_PASSWORD` are missing or the credentials are
wrong. `GET /api/v1/health` returns `"connected": false` and the mode `stub`.
Check `.env` at the repo root.

## Control unavailable / "No response from device"

`GET /api/v1/health` now reports `control.available` + `control.reason` and a
`cloud_error` field — read those first, they state exactly what is wrong:

- **`cloud login failed: Xiaomi rejected the credentials (70016)`** — the
  legacy Xiaomi auth path was used (wrong ref clone). The server auto-picks a
  ref with the Dreame-native class; if it still fails, ensure `DREAME_REF_PATH`
  points at `tasshack_dreame_vacuum_ref` (v2 fork), not upstream v1
  (`dreame-vacuum`). See [The Dreame Robo Hoover Saga](ROBO_HOOVER_SAGA.md).
- **`local path down: robot did not answer UDP miio at ...`** — the null-token
  trick is dead on current firmware; the cloud fallback should take over. If
  cloud login also failed, check credentials/region or wait out a rate limit.
- **Transient cloud failures after repeated logins** — DreameHome rate-limits
  auth; wait a few minutes and retry (`restart` the backend or call
  `POST /api/v1/shutdown` then restart).

## Map request hangs or times out

- Cloud map fetches can take up to 60s (`MAP_FETCH_TIMEOUT`); the server
  serializes map fetches — wait for the response.
- The cloud map path needs `DREAME_USER`/`DREAME_PASSWORD` (login) and
  resolves the object name + signed URL automatically. The rendered PNG is
  also served at `GET /api/v1/map/png`.
- "Render error" in the map output means the PNG renderer failed; raw map
  data is still available via `raw_b64`.

## Agentic workflow returns "Workflow failed"

`ctx.sample()` requires a host that supports MCP sampling (Claude Desktop,
Cursor). Hosts without sampling get a structured error — use `dreame_tool`
directly instead.

## LLM chat says no provider

The chat probes Ollama at `http://127.0.0.1:11434` (`OLLAMA_BASE_URL`).
Start Ollama (`ollama serve`) and pull a model (`ollama pull llama3.2:3b`).

## Native (Tauri) build issues

- PyInstaller spec: `dreame-mcp-backend.spec`; entry `run_server.py`.
- The spec's SKIP list must not include `cryptography`/`crypto` (OpenSSL DLLs).
- `just build-native` then `just cua-nsis-test` (install → launch → nav walk → uninstall).
