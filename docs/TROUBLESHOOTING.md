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

## Robot shows "Not configured" vs "Offline"

These are different states — read `mode` in `GET /api/v1/health` first:

- **`unconfigured`** — no credentials in `.env` at all. Set
  `DREAME_USER`/`DREAME_PASSWORD` (cloud) or `DREAME_IP` (local), then
  restart the backend.
- **`offline`** — credentials exist but the robot is unreachable. `control.reason`
  and `startup_error` name the exact cause (local UDP path down and/or cloud
  login error). Do NOT re-enter credentials for this — fix the robot's
  network instead (see below).

## Robot lost Wi-Fi / offline in the DreameHome app

This is a robot-side network drop, not a server bug. Confirm it before touching
config:

1. The robot is missing from the router's DHCP client list and its last IP
   does not answer ping.
2. `uv run python scripts/discover.py` from the repo root finds no miio
   device (UDP 54321) anywhere on the LAN.

Re-establish the connection (maps and settings survive a Wi-Fi reset):

1. **Pairing mode**: robot on and docked, press and HOLD the Home button
   3–5 s until the voice prompt ("waiting for connection") and the Wi-Fi
   light blinks slowly. No prompt → power-cycle (lift off dock, hold power
   ~5 s to shut down, wait 10 s, power on, re-dock) and retry.
2. **Re-pair**: DreameHome app → `+` → follow the prompts. Keep Bluetooth on
   and the phone within 1–2 m (BLE discovery), then join the robot's
   temporary `dreame-vacuum-xxxx` hotspot when asked so the app can hand
   over your home credentials.
3. **2.4 GHz only** — the robot cannot see 5 GHz. Join the phone to the
   2.4 GHz side during setup; WPA2, no VPN on the phone, no MAC
   filtering / AP isolation on the router.
4. **Pin the IP**: give the robot a DHCP reservation in the router, put the
   (usually new) IP in `DREAME_IP` in `.env`, restart the backend once.
5. **Cloud password**: if the cloud path reports `user password not match`,
   whatever logs you into the app is the truth — put that exact string in
   `DREAME_PASSWORD`. DreameHome allows ~5 login attempts, so do not spam
   restarts while guessing.

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
