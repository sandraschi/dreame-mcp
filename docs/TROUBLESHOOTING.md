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

## Map request hangs or times out

- Cloud map fetches can take up to 60s (`MAP_FETCH_TIMEOUT`); the server
  serializes map fetches — wait for the response.
- "Render error" in the map output means the PNG renderer failed; raw map data
  is still available via `raw_b64`.
- Hybrid mode (local IP + cloud credentials) gives the fastest map path.

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
