"""Pytest configuration for dreame-mcp — dual-mode test scaffold.

Modes:
    MOCKED (default, CI):  Uses synthetic fixtures. No cloud credentials needed.
    LIVE (IRL with hoover): Requires DREAME_USER + DREAME_PASSWORD env vars.
                            Set DREAME_LIVE=1 to enable.

Usage:
    uv run pytest                          # mocked (CI-safe)
    DREAME_LIVE=1 uv run pytest            # live against real hoover
    uv run pytest -k "test_map"            # just map tests
    uv run pytest --live                   # CLI flag for live mode
"""

from __future__ import annotations

import base64
import os
from unittest.mock import AsyncMock, MagicMock

import pytest

from dreame_mcp.client import DreameHomeClient, DreameStatus
from dreame_mcp.state import _state

# ---------------------------------------------------------------------------
# CLI option: --live flag
# ---------------------------------------------------------------------------


def pytest_addoption(parser):
    parser.addoption("--live", action="store_true", default=False, help="Run tests against live hoover")


def pytest_configure(config):
    config.addinivalue_line("markers", "live: marks tests that require a real Dreame hoover")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--live") or os.environ.get("DREAME_LIVE", "").strip() == "1":
        return  # don't skip live tests
    skip_live = pytest.mark.skip(reason="Needs --live flag or DREAME_LIVE=1")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)


# ---------------------------------------------------------------------------
# Fixtures: synthetic map data
# ---------------------------------------------------------------------------

# 1x1 red PNG (smallest valid PNG for testing)
_TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0c"
    b"IDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00"
    b"\x00\x00IEND\xaeB`\x82"
)

# Synthetic occupancy grid (10x10, 0=free, 100=occupied, -1=unknown)
_MOCK_OCCUPANCY_GRID = [
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    100,
    100,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    100,
    100,
    0,
    0,
    100,
    100,
    0,
    0,
    0,
    0,
    100,
    100,
    0,
    0,
    100,
    100,
    0,
    0,
    0,
    0,
    100,
    100,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    100,
    100,
    0,
    0,
    0,
    0,
    0,
    100,
    100,
    0,
    100,
    100,
    0,
    0,
    0,
    0,
    0,
    100,
    100,
    0,
    100,
    100,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
]


@pytest.fixture
def tiny_png_bytes():
    """Smallest valid PNG for map render tests."""
    return _TINY_PNG


@pytest.fixture
def tiny_png_b64():
    """Base64-encoded tiny PNG."""
    return base64.b64encode(_TINY_PNG).decode()


@pytest.fixture
def mock_map_response(tiny_png_b64):
    """Synthetic successful map response matching DreameHomeClient.get_map() shape."""
    raw_bytes = b"\x00" * 256  # fake raw map blob
    return {
        "success": True,
        "object_name": "dreame.vacuum.r2566a/12345/2045852486/0",
        "raw_bytes": len(raw_bytes),
        "image": tiny_png_b64,
        "map_data": {
            "rooms": 3,
            "robot_position": {"x": 25500, "y": 25500},
            "charger_position": {"x": 25000, "y": 25000},
        },
        "raw_b64": base64.b64encode(raw_bytes).decode(),
    }


@pytest.fixture
def mock_map_response_no_image():
    """Map response without rendered image (raw_b64 only, render failed)."""
    raw_bytes = b"\x00" * 128
    return {
        "success": True,
        "object_name": "dreame.vacuum.r2566a/12345/2045852486/0",
        "raw_bytes": len(raw_bytes),
        "raw_b64": base64.b64encode(raw_bytes).decode(),
        "render_error": "Map decode failed: missing py_mini_racer",
    }


@pytest.fixture
def mock_map_timeout_response():
    """Map response when cloud times out."""
    return {
        "success": False,
        "error": "Map request timed out (45s). DreameHome cloud may be unreachable.",
        "timeout": True,
    }


@pytest.fixture
def mock_status():
    """Synthetic DreameStatus."""
    return DreameStatus(
        state="charging",
        battery=72,
        fan_speed="1",
        is_charging=True,
        is_cleaning=False,
        cleaned_area=23.5,
        cleaning_time=1800,
        raw={"2.1": 3, "3.1": 72, "3.2": 1, "4.2": 1800, "4.3": 235000, "4.4": 1},
    )


@pytest.fixture
def occupancy_grid():
    """10x10 mock occupancy grid (ROS2 nav_msgs/OccupancyGrid compatible)."""
    return {
        "width": 10,
        "height": 10,
        "resolution": 0.05,  # meters per pixel
        "origin": {"x": -0.25, "y": -0.25, "yaw": 0.0},
        "data": _MOCK_OCCUPANCY_GRID,
    }


# ---------------------------------------------------------------------------
# Fixtures: mocked client
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client(mock_status, mock_map_response):
    """Fully mocked DreameHomeClient — no cloud calls."""
    client = MagicMock(spec=DreameHomeClient)
    client.connected = True
    client._did = "2045852486"
    client.auth_key = "mock_auth_key_1234567890"

    # Async mocks
    client.get_status = AsyncMock(return_value=mock_status)
    client.get_map = AsyncMock(return_value=mock_map_response)
    client.control = AsyncMock(return_value={"success": True, "message": "Sent start_clean"})
    client.connect = AsyncMock(return_value=True)
    client.disconnect = MagicMock()

    return client


@pytest.fixture
def patched_state(mock_client):
    """Inject mock client into global state, restore after test."""
    original = _state.get("client")
    _state["client"] = mock_client
    yield mock_client
    _state["client"] = original


# ---------------------------------------------------------------------------
# Fixtures: live client (IRL only)
# ---------------------------------------------------------------------------


@pytest.fixture
def live_client():
    """Real DreameHomeClient from env vars. Only used with @pytest.mark.live."""
    from dreame_mcp.client import client_from_env

    client = client_from_env()
    if client is None:
        pytest.skip("No DREAME_USER/DREAME_PASSWORD set")
    return client


@pytest.fixture
async def connected_live_client(live_client):
    """Connected live client. Async fixture — connects then disconnects."""
    ok = await live_client.connect()
    if not ok:
        pytest.skip("Live connection failed")
    yield live_client
    live_client.disconnect()
