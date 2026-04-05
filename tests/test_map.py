"""Tests for LIDAR map download — the critical path.

Covers:
    - Mocked: map fetch success (with/without image), timeout, not-connected
    - Mocked: map export to PGM/YAML (ROS2 OccupancyGrid standard)
    - Mocked: map export to PNG (direct download)
    - Live: real map fetch from DreameHome cloud (IRL only)
"""
from __future__ import annotations

import asyncio
import base64
import io

import pytest

from dreame_mcp.client import MAP_FETCH_TIMEOUT, DreameHomeClient
from dreame_mcp.portmanteau import dreame_tool
from dreame_mcp.state import _state

# ======================================================================
# MOCKED TESTS (CI-safe, no cloud credentials)
# ======================================================================


class TestMapFetchMocked:
    """Map download via portmanteau tool with mocked client."""

    @pytest.mark.asyncio
    async def test_map_success_with_image(self, patched_state, mock_map_response):
        """Map fetch returns base64 PNG + raw_b64 + map_data."""
        result = await dreame_tool(ctx=None, operation="map")
        assert result["success"] is True
        assert "image" in result           # rendered PNG
        assert "raw_b64" in result         # raw fallback
        assert "map_data" in result
        assert result["map_data"]["rooms"] == 3
        assert result["raw_bytes"] > 0

    @pytest.mark.asyncio
    async def test_map_success_without_image(self, patched_state, mock_map_response_no_image):
        """Map fetch without rendering — raw_b64 still returned."""
        patched_state.get_map.return_value = mock_map_response_no_image
        result = await dreame_tool(ctx=None, operation="map")
        assert result["success"] is True
        assert "image" not in result
        assert "raw_b64" in result
        assert "render_error" in result

    @pytest.mark.asyncio
    async def test_map_not_connected(self):
        """Map fetch with no client returns stub."""
        original = _state.get("client")
        _state["client"] = None
        try:
            result = await dreame_tool(ctx=None, operation="map")
            assert result["success"] is True
            assert "message" in result  # stub message
        finally:
            _state["client"] = original

    @pytest.mark.asyncio
    async def test_map_timeout(self, patched_state, mock_map_timeout_response):
        """Map fetch timeout returns descriptive error."""
        patched_state.get_map.return_value = mock_map_timeout_response
        result = await dreame_tool(ctx=None, operation="map")
        assert result["success"] is False
        assert "timed out" in result.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_map_cloud_failure(self, patched_state):
        """Map fetch cloud failure returns diagnostic info."""
        patched_state.get_map.return_value = {
            "success": False,
            "error": "Map fetch failed (cloud returned no file data)",
            "diagnostic_info": {
                "did": "2045852486",
                "object_name": "dreame.vacuum.r2566a/12345/2045852486/0",
                "attempted": [{"filename": "test", "type": "map"}],
            },
        }
        result = await dreame_tool(ctx=None, operation="map")
        assert result["success"] is False
        assert "diagnostic_info" in result


class TestMapExportFormats:
    """Map export to standard formats (PGM/YAML, PNG)."""

    def test_raw_b64_decodable(self, mock_map_response):
        """raw_b64 is valid base64 that decodes to bytes."""
        raw = base64.b64decode(mock_map_response["raw_b64"])
        assert isinstance(raw, bytes)
        assert len(raw) == mock_map_response["raw_bytes"]

    def test_image_b64_is_valid_png(self, mock_map_response, tiny_png_bytes):
        """image field is base64-encoded PNG with valid PNG header."""
        img_bytes = base64.b64decode(mock_map_response["image"])
        assert img_bytes[:4] == b"\x89PNG"
        assert img_bytes == tiny_png_bytes

    def test_occupancy_grid_shape(self, occupancy_grid):
        """Occupancy grid has correct dimensions and value range."""
        g = occupancy_grid
        assert len(g["data"]) == g["width"] * g["height"]
        for val in g["data"]:
            assert val in range(-1, 101), f"Invalid occupancy value: {val}"
        assert g["resolution"] > 0

    def test_occupancy_grid_to_pgm(self, occupancy_grid):
        """Convert occupancy grid to PGM format (ROS2 nav2_map_server standard)."""
        g = occupancy_grid
        pgm = _occupancy_to_pgm(g["data"], g["width"], g["height"])
        # PGM starts with P5 magic
        assert pgm[:2] == b"P5"
        # Parse dimensions from header
        lines = pgm.split(b"\n", 3)
        assert lines[0] == b"P5"
        w, h = lines[1].split()
        assert int(w) == g["width"]
        assert int(h) == g["height"]

    def test_occupancy_grid_to_yaml(self, occupancy_grid):
        """Generate ROS2 map YAML metadata."""
        g = occupancy_grid
        yaml_str = _occupancy_to_yaml(
            image_filename="dreame_map.pgm",
            resolution=g["resolution"],
            origin=(g["origin"]["x"], g["origin"]["y"], g["origin"]["yaw"]),
        )
        assert "image: dreame_map.pgm" in yaml_str
        assert "resolution: 0.05" in yaml_str
        assert "occupied_thresh: 0.65" in yaml_str
        assert "free_thresh: 0.196" in yaml_str


class TestStatusMocked:
    """Status operations with mocked client."""

    @pytest.mark.asyncio
    async def test_status_success(self, patched_state):
        result = await dreame_tool(ctx=None, operation="status")
        assert result["success"] is True
        assert result["battery"] == 72
        assert result["state"] == "charging"

    @pytest.mark.asyncio
    async def test_battery_shortcut(self, patched_state):
        result = await dreame_tool(ctx=None, operation="battery")
        assert result["success"] is True
        assert result["battery"] == 72

    @pytest.mark.asyncio
    async def test_unknown_operation(self, patched_state):
        result = await dreame_tool(ctx=None, operation="dance")
        assert result["success"] is False
        assert "Unknown operation" in result["error"]


class TestControlMocked:
    """Control commands with mocked client."""

    @pytest.mark.asyncio
    async def test_start_clean(self, patched_state):
        result = await dreame_tool(ctx=None, operation="start_clean")
        assert result["success"] is True
        patched_state.control.assert_called_once_with("start_clean")

    @pytest.mark.asyncio
    async def test_find_robot(self, patched_state):
        """The 'I am here' chirp command."""
        result = await dreame_tool(ctx=None, operation="find_robot")
        assert result["success"] is True
        patched_state.control.assert_called_once_with("find_robot")


class TestClientTimeouts:
    """Verify timeout constants are sensible."""

    def test_map_timeout_value(self):
        assert MAP_FETCH_TIMEOUT == 45

    def test_executor_pool_size(self):
        client = DreameHomeClient("user", "pass")
        assert client._executor._max_workers == 4
        client._executor.shutdown(wait=False)


# ======================================================================
# LIVE TESTS (IRL only — requires --live or DREAME_LIVE=1)
# ======================================================================


@pytest.mark.live
class TestMapFetchLive:
    """Real map download from DreameHome cloud."""

    @pytest.mark.asyncio
    async def test_live_map_fetch(self, connected_live_client):
        """Fetch real map — should return success with raw_b64."""
        result = await connected_live_client.get_map()
        assert result["success"] is True, f"Live map fetch failed: {result.get('error')}"
        assert "raw_b64" in result, "Missing raw_b64 in live map response"
        raw = base64.b64decode(result["raw_b64"])
        assert len(raw) > 0, "raw_b64 decoded to empty bytes"
        print(f"\n  Live map: {len(raw)} bytes, object_name={result.get('object_name')}")
        if "image" in result:
            img = base64.b64decode(result["image"])
            assert img[:4] == b"\x89PNG"
            print(f"  Rendered PNG: {len(img)} bytes")
        if "map_data" in result:
            print(f"  Map data: rooms={result['map_data'].get('rooms')}")

    @pytest.mark.asyncio
    async def test_live_map_does_not_hang(self, connected_live_client):
        """Map fetch must complete within MAP_FETCH_TIMEOUT (no hang regression)."""
        result = await asyncio.wait_for(
            connected_live_client.get_map(),
            timeout=MAP_FETCH_TIMEOUT + 5,
        )
        # Even if map isn't available, it should return — not hang
        assert "success" in result

    @pytest.mark.asyncio
    async def test_live_status(self, connected_live_client):
        """Fetch real status — battery and state."""
        status = await connected_live_client.get_status()
        assert status.error is None, f"Live status error: {status.error}"
        assert 0 <= status.battery <= 100
        print(f"\n  Live status: battery={status.battery}%, state={status.state}")

    @pytest.mark.asyncio
    async def test_live_find_robot(self, connected_live_client):
        """The hoover says 'I am here'. Only run this if you want to hear it!"""
        result = await connected_live_client.control("find_robot")
        assert result["success"] is True, f"find_robot failed: {result.get('error')}"
        print("\n  ✅ Hoover chirped!")


# ======================================================================
# Helpers: PGM/YAML export (used in tests, also exported for server)
# ======================================================================


def _occupancy_to_pgm(data: list[int], width: int, height: int) -> bytes:
    """Convert OccupancyGrid data to PGM (Portable Gray Map) binary format.

    ROS2 convention: white=free(0), black=occupied(100), gray=unknown(-1).
    PGM: 0=black, 255=white. So we invert: free→254, occupied→0, unknown→205.
    """
    buf = io.BytesIO()
    buf.write(f"P5\n{width} {height}\n255\n".encode())
    for val in data:
        if val == -1:
            buf.write(bytes([205]))   # unknown → mid-gray
        elif val >= 0:
            pixel = int(254 * (1.0 - val / 100.0))
            buf.write(bytes([max(0, min(254, pixel))]))
        else:
            buf.write(bytes([205]))
    return buf.getvalue()


def _occupancy_to_yaml(
    image_filename: str,
    resolution: float,
    origin: tuple[float, float, float],
    occupied_thresh: float = 0.65,
    free_thresh: float = 0.196,
) -> str:
    """Generate ROS2 nav2_map_server compatible YAML metadata."""
    return (
        f"image: {image_filename}\n"
        f"resolution: {resolution}\n"
        f"origin: [{origin[0]}, {origin[1]}, {origin[2]}]\n"
        f"occupied_thresh: {occupied_thresh}\n"
        f"free_thresh: {free_thresh}\n"
        f"negate: 0\n"
        f"mode: trinary\n"
    )
