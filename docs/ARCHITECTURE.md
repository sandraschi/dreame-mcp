# Architecture: Dreame Hybrid Bridge

This document explains the internal architecture of `dreame-mcp` and how it handles the "Hybrid" connection model between local MiIO and the DreameHome Cloud.

## Unified Protocol Layer

The backend uses a **Hybrid Client** (`DreameHomeClient`) that wraps the external `DreameVacuumProtocol` from the Tasshack reference. This allows the system to maintain two independent communication channels for the same device.

### 1. Local Control (MiIO)
- **Path**: Direct UDP (Port 54321) to the robot's IP.
- **Protocol**: MiIO formatted packets.
- **The Null Token Trick**: In many circumvention setups (bridged or modified firmware), the vacuum is configured to accept a "Null Token" (`000...000`) for local commands. `dreame-mcp` automatically defaults to this value if `DREAME_IP` is set but `DREAME_TOKEN` is blank.
- **Used for**: `start`, `stop`, `pause`, `go_home`, `find_robot`, and real-time status (battery, cleaning state).

### 2. Cloud Telemetry (Maps)
- **Path**: HTTPS to Dreame/Xiaomi Cloud API.
- **Credentials**: `DREAME_USER` + `DREAME_PASSWORD`.
- **The Map Stream**: LIDAR maps are uploaded by the robot to the cloud as encrypted blobs. The backend fetches these blobs, decrypts them using session-derived keys, and renders them to PNG using `Pillow` and `py-mini-racer`.
- **Used for**: LIDAR Maps, Real-time Robot Position (coordinates), and floor plan metadata.

## Service Mapping

When an MCP tool or REST API call is made, the backend performs "Intelligent Routing":

| Request | Route | Implementation |
| :--- | :--- | :--- |
| **Control** (Start) | ⚡ Local | Direct UDP Packet (Fast) |
| **Status** (Battery) | ⚡ Local | Direct UDP Packet (Fast) |
| **Telemetry** (Map) | ☁️ Cloud | HTTPS Cloud Fetch (Slow) |

## Dependency Chain

- **`src/dreame_mcp`**: The MCP and FastAPI web server layer.
- **`DREAME_REF_PATH`**: A local clone of the core protocol library (`dreame-vacuum`) which contains the heavy lifting for decryption and map rendering.
- **`python-dotenv`**: Used to load your `.env` secrets into the process environment.

## MCP tool vs structured fetchers

The FastMCP tool `dreame(operation=...)` returns **Markdown** (optimized for LLM context in the chat). The same logic used by REST is exposed as async functions in `dreame_mcp.portmanteau`: `fetch_status_data`, `fetch_map_data`, and `execute_control_data`, each returning a **JSON-serializable dict** (e.g. `success`, `battery`, `error`). Tests in `tests/test_map.py` cover both layers.

---

> [!TIP]
> **Why Hybrid?** Normal cloud-only integrations suffer from 1-3 seconds of latency for simple commands. Hybrid mode ensures that when you click "Start," the vacuum reacts **instantly** over your local WiFi, even while the high-fidelity map is still loading from the cloud.
