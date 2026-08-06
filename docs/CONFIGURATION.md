# Configuration

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `DREAME_USER` | for maps | DreameHome email or phone |
| `DREAME_PASSWORD` | for maps | DreameHome password |
| `DREAME_COUNTRY` | no | Cloud region, default `eu` |
| `DREAME_DID` | no | Device ID, auto-discovered when a single device |
| `DREAME_AUTH_KEY` | no | Refresh token from a previous login (speeds up startup) |
| `DREAME_REF_PATH` | no | Path to the Tasshack dreame-vacuum reference clone |
| `DREAME_MCP_PORT` | no | Backend port (default `10894`) |
| `DREAME_MCP_HOST` | no | Backend bind host (default `127.0.0.1`) |
| `DREAME_IP` / `DREAME_TOKEN` | hybrid only | Local miio (null-token trick when token blank) |
| `OLLAMA_BASE_URL` | no | LLM chat backend (default `http://127.0.0.1:11434`) |

Copy `.env.example` to `.env` and fill in your details. The `.env` file lives at
the repo root only — one source of truth (no fallback chains).

### The Tasshack reference clone

The protocol layer is bootstrapped from an external clone of
`Tasshack/dreame-vacuum`. **Use the v2 fork, not the upstream v1 repo** —
upstream v1 renamed the Dreame-native cloud class and only ships the legacy
Xiaomi auth flow, which rejects DreameHome accounts. The canonical path is
`D:\Dev\repos\external\tasshack_dreame_vacuum_ref`; the server also
auto-discovers candidates and prefers any clone that ships
`DreameVacuumDreameHomeCloudProtocol`, so a wrong `DREAME_REF_PATH` no longer
breaks the cloud path.

See [The Dreame Robo Hoover Saga](ROBO_HOOVER_SAGA.md) for the full story of
how control was lost and restored.

## Connection modes

| Mode | Credentials | Commands | LIDAR Map |
|---|---|---|---|
| Local | `DREAME_IP` | local UDP miio | no |
| Cloud | `DREAME_USER` + `DREAME_PASSWORD` | cloud (DreameHome API) | yes |
| Hybrid (recommended) | both | local first, cloud fallback | yes |

The cloud path (Dreame-native `api.dreame.tech`) is the reliable one — it works
even when the robot does not answer UDP miio (the null-token trick no longer
works on current firmware). Control/status/map all fall back to the cloud
automatically when the local path fails.

## Ports

- Backend (REST + MCP): **10894**
- Webapp (Vite dev): **10895**

## Runtime state

The server keeps a single in-memory `_state` dict (`client`, `client.connected`).
No database is used; the activity log is an in-memory ring buffer (5000 entries).
