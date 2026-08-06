# The Dreame Robo Hoover Saga

*How we controlled the D20 Pro Plus, broke it, and fixed it — with the LIDAR
map as a bonus. Written 2026-08-06 after a full day of network forensics,
cloud-protocol archaeology, and two ref clones.*

---

## Act I — It worked (2025)

For a while, the Dreame D20 Pro Plus answered to `dreame-mcp`. Commands went
out, the hoover cleaned, `find_robot` chirped. That path used **local miio
control** — UDP to the robot on port 54321 with a token (originally extracted
via Home Assistant's Dreame integration), plus the DreameHome cloud for maps.

The important detail: back then, **the LAN path worked**. The robot answered
the miio hello, the token (or the null-token trick) was accepted, and
`start_clean` / `go_home` just worked.

## Act II — The breakage (early 2026)

Two things happened, and they compounded:

### 1. The v0.2+ cloud/hybrid rework

The client was rewritten around the Tasshack `dreame-vacuum` reference clone:
`DreameVacuumProtocol` for local + cloud, with a Dreame-native cloud class
(`DreameVacuumDreameHomeCloudProtocol`) for DreameHome accounts. The code was
written against a **fork of `v2.0.0b22`** (local commit 2026-04-17).

### 2. The ref clone swap (the actual "we broke it" moment)

Someone pulled the **upstream `v1.0.9`** repo (`dreame-vacuum`, 2026-04-26)
and repointed `DREAME_REF_PATH` in `.env` at it. Upstream had **renamed** the
Dreame-native cloud class:

| Ref clone | Cloud class | DreameHome accounts |
|---|---|---|
| `tasshack_dreame_vacuum_ref` (v2.0.0b22 fork) | `DreameVacuumDreameHomeCloudProtocol` | ✅ works (`api.dreame.tech`) |
| `dreame-vacuum` (upstream v1.0.9) | `DreameVacuumCloudProtocol` | ❌ legacy Xiaomi auth |

With the wrong ref loaded:

- `_cloud_cls` looked for `DreameVacuumDreameHomeCloudProtocol` → not found →
  cloud control path silently missing.
- The unified protocol's built-in cloud used the **legacy Xiaomi login**
  (`account.xiaomi.com`, `sid=xiaomiio`) which rejects DreameHome accounts
  with **error code 70016** (wrong username/password from Xiaomi's
  perspective — the account simply isn't a Xiaomi account).
- Meanwhile the robot's firmware had moved on: the **null-token UDP trick
  stopped working**. The robot is on the LAN (router shows
  `dreame_vacuum_r2566a` on Wi-Fi 2.4G) but no longer answers the miio hello
  to a null token — so the local control path died too.

Result: both control paths dead. Status returned "No response from device",
control returned nothing, and the dashboard said "Not configured" while the
robot happily vacuumed on its own schedule.

## Act III — The diagnosis (2026-08-06)

1. **Live connect test** showed the exact failure:
   `Cloud login failed — local-only mode` + `Unable to discover the device
   192.168.0.178` (UDP).
2. **Router DHCP table**: robot IS online at `192.168.0.178` (MAC
   `00:AE:F7:0B:CC:FF`, hostname `dreame_vacuum_r2566a`). So it was firmware,
   not connectivity — it just ignores null-token discovery.
3. **Two ref clones discovered** on disk. `tasshack_dreame_vacuum_ref` has the
   class name the code was written against. `.env` pointed at the other one.
4. **Direct login test with the v2 ref + `account_type="dreame"`**:
   ✅ `login()` → JWT auth key → `get_devices()` → 1 device
   (`dreame.vacuum.r2566a`, D20 Pro Plus, DID `2045852486`).
5. **The 404 wall**: `sendCommand` to `eu.iot.dreame.tech:13267` returned
   `404 NOT_FOUND`. The device record's **`bindDomain`**
   (`10000.mt.eu.iot.dreame.tech:19973`) is the routing secret — the class
   appends `-10000` to the API path when `_host` is set. With
   `cloud._host = bindDomain`:
   ✅ `get_properties` → `[{siid: 3, piid: 1, value: 98}]` — **battery 98%,
   live**.
6. **The map**: `get_device_info()` populates `_model`/`_uid`, then
   `get_interim_file_url(object_name)` returns a signed URL to
   `awsde0.fds.api.xiaomi.com`, `get_file` downloads the raw map blob, the
   Tasshack decoder + renderer turn it into a PNG.

## Act IV — The fix

All in `src/dreame_mcp/client.py` (plus a discovery helper):

1. **Ref resolution is now automatic**: `_resolve_ref_dir()` prefers any clone
   that ships `DreameVacuumDreameHomeCloudProtocol`, falling back to
   candidates, so a wrong `DREAME_REF_PATH` can no longer silently break the
   cloud path.
2. **Dreame-native cloud client**: `self._dreame_cloud` is built on connect
   (`account_type="dreame"`), logs in, resolves DID + `bindDomain` host from
   `get_devices()`, and calls `get_device_info()` for `_model`/`_uid`.
3. **Cloud fallback everywhere**: `_safe_call()` falls back to the
   Dreame-native cloud when the local path fails — status (`get_properties`),
   control (`action`), and map file retrieval (`get_interim_file_url` /
   `get_file` / `get_device_file`) all route through it.
4. **Connect now succeeds on cloud alone** (no LAN needed).
5. **Errors are surfaced**: `/api/v1/health` reports `control.available`,
   `control.reason`, and `cloud_error` (with Xiaomi 70016 / 2FA / captcha
   classification) — no more silent stub mode.
6. **`scripts/discover.py` + `just check-discovery`** — a working LAN sweep
   (the old recipe `python -m miio discover` was broken: miio has no
   `__main__`).

### Proof (live, 2026-08-06)

```
HEALTH:  connected=True  control.available=True
STATUS:  battery=98  state=charging  is_charging=True     (via cloud fallback)
CONTROL: find_robot -> {"success": true, "result": {"code": 0}}   (robot chirped)
MAP:     raw_bytes=16768 -> decoded -> rendered PNG (19828 bytes, 1 room)
```

## Act V — Lessons

- **Pin the ref clone.** The protocol layer comes from an external repo; a
  silent upstream rename breaks the cloud path with no error. The code now
  *detects* which ref it's talking to instead of trusting a path.
- **DreameHome accounts are not Xiaomi accounts.** 70016 from
  `account.xiaomi.com` is a red herring for "wrong backend", not "wrong
  password". The Dreame-native API (`api.dreame.tech`, `account_type="dreame"`)
  is the correct door.
- **`bindDomain` is the routing key.** Without setting `cloud._host` from the
  device record, the API 404s even with a valid login.
- **The null-token trick is dead on current firmware.** Don't rely on it;
  the cloud path is the dependable one now.
- **Rate limits are real.** Hammering the login endpoint in quick succession
  causes transient failures that look like credential errors. Pace the tests.

## Current status (2026-08-06)

- ✅ Status, control, and LIDAR map all work via the DreameHome cloud,
  LAN-free.
- ✅ Local UDP is still attempted first (works on firmware that answers);
  cloud is the fallback.
- ✅ `GET /api/v1/map/png` serves the rendered floor plan.
- 📌 If the robot ever stops answering the cloud, check
  `GET /api/v1/health` → `control.reason` and `cloud_error` first — they now
  say exactly what is wrong.

## Act VI — Boomy gets the map

The floor plan is an asset for other domestic robots. **yahboom-mcp** (Boomy,
the Raspbot) now consumes it three ways:

1. **MCP tool** — `lidar(operation="read_dreame_map")` GETs `DREAME_MAP_URL`
   (default `http://127.0.0.1:10894/api/v1/map`).
2. **Webapp** — Lidar Map page fetches `GET /api/v1/lidar/dreame-map` (REST
   proxy added 2026-08-06) and renders the floorplan.
3. **ROS2 / Nav2** — `ros2/boomy_dreame_map_bridge` polls the same URL and
   publishes a `nav_msgs/OccupancyGrid` on `/dreame_floorplan` as a static
   layer (the Raspbot's own MS200 `/scan` remains the live obstacle source).

Verified end-to-end: yahboom `/api/v1/lidar/dreame-map` → dreame-mcp cloud map
→ 16,768 raw bytes → 19,828-byte PNG, one room, battery 98%.
