# Onboarding

## What you need

1. A **Dreame robot vacuum** (D20 Pro Plus or similar DreameHome-compatible model).
2. A **DreameHome account** (email or phone) with the robot bound to it.
   Get one from the DreameHome app (iOS/Android/Web).
3. Your **cloud region** (most of Europe is `eu`; China is `cn`, US is `us`).

## Step 1 — Configure credentials

Copy `.env.example` to `.env` at the repo root and set:

```ini
DREAME_USER=your@email.com
DREAME_PASSWORD=your_password
DREAME_COUNTRY=eu
```

Optional but recommended: `DREAME_DID` (device id). It is auto-discovered when
your account has exactly one Dreame device.

## Step 2 — Start the stack

```powershell
.\webapp\start.ps1
```

The dashboard opens at `http://localhost:10895`. The backend health check at
`http://localhost:10894/api/v1/health` should report `"connected": true` with
your DID once the cloud login succeeds.

## Step 3 — Verify

1. Dashboard shows the robot as Connected (green dot).
2. `GET /api/v1/status` returns battery + state.
3. LIDAR Map page renders rooms (requires the robot to have done at least one
   full mapping run — press clean once if the map is empty).
4. Try `POST /api/v1/control/go_home`.

## Not configured yet?

Until credentials are set, the server runs in **stub mode** (declared mock data)
so the UI and MCP surface still work. Status/control calls return a clear
"set DREAME_USER/DREAME_PASSWORD" message — this is intentional, not a bug.
