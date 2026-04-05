"""Map export — convert Dreame map data to standard robotics formats.

Formats:
    PGM   — Portable Gray Map (ROS2 nav2_map_server standard)
    YAML  — Map metadata for nav2_map_server
    PNG   — Rendered floor plan image (direct from Tasshack if available)

ROS2 OccupancyGrid standard:
    - PGM + YAML pair loaded by nav2_map_server
    - Topic: /map (nav_msgs/msg/OccupancyGrid)
    - Cell values: 0=free, 100=occupied, -1=unknown
    - PGM pixel values: 254=free(white), 0=occupied(black), 205=unknown(gray)
    - Resolution: meters per pixel (typically 0.05)

The Dreame vacuum's proprietary map blob is decoded by the Tasshack map layer.
This module bridges the gap: Tasshack decoded data → standard ROS2/PGM/PNG exports.
"""
from __future__ import annotations

import base64
import io
import logging

logger = logging.getLogger("dreame-mcp.map_export")


def occupancy_to_pgm(data: list[int], width: int, height: int) -> bytes:
    """Convert OccupancyGrid data array to PGM (Portable Gray Map) binary.

    ROS2 convention: 0=free, 100=occupied, -1=unknown.
    PGM convention: 0=black, 255=white.
    Mapping: free(0)→254(white), occupied(100)→0(black), unknown(-1)→205(gray).

    Args:
        data: Flat list of occupancy values (row-major, top-left origin).
        width: Grid width in cells.
        height: Grid height in cells.

    Returns:
        Raw PGM file bytes (P5 binary format).
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


def occupancy_to_yaml(
    image_filename: str,
    resolution: float,
    origin: tuple[float, float, float],
    occupied_thresh: float = 0.65,
    free_thresh: float = 0.196,
) -> str:
    """Generate ROS2 nav2_map_server compatible YAML metadata.

    This YAML file is loaded alongside the PGM by nav2_map_server to
    publish a nav_msgs/msg/OccupancyGrid on the /map topic.

    Args:
        image_filename: Relative path to the PGM file.
        resolution: Meters per pixel.
        origin: (x, y, yaw) of the lower-left pixel in world frame.
        occupied_thresh: Pixel probability above this = occupied.
        free_thresh: Pixel probability below this = free.

    Returns:
        YAML string.
    """
    return (
        f"image: {image_filename}\n"
        f"resolution: {resolution}\n"
        f"origin: [{origin[0]}, {origin[1]}, {origin[2]}]\n"
        f"occupied_thresh: {occupied_thresh}\n"
        f"free_thresh: {free_thresh}\n"
        f"negate: 0\n"
        f"mode: trinary\n"
    )


def map_response_to_png_bytes(map_response: dict) -> bytes | None:
    """Extract PNG bytes from a dreame_tool(operation='map') response.

    Tries 'image' (base64 PNG) first, returns None if unavailable.
    """
    img_b64 = map_response.get("image")
    if not img_b64 or not isinstance(img_b64, str):
        return None
    try:
        data = base64.b64decode(img_b64)
        if data[:4] == b"\x89PNG":
            return data
    except Exception:
        pass
    return None


def map_response_to_raw_bytes(map_response: dict) -> bytes | None:
    """Extract raw map bytes from a dreame_tool(operation='map') response.

    Returns the decoded raw_b64 field — the proprietary Dreame map blob
    that the Tasshack map layer can decode, or that custom pipeline
    decoders (robotics-mcp, yahboom-mcp) can process.
    """
    raw_b64 = map_response.get("raw_b64")
    if not raw_b64 or not isinstance(raw_b64, str):
        return None
    try:
        return base64.b64decode(raw_b64)
    except Exception:
        return None
