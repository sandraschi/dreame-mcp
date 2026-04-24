"""Deep diagnostic for Dreame map fetch — comparing get_device_file vs get_file_url."""

import asyncio
import logging
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from dreame_mcp.client import _REF_DEFAULT, _bootstrap_protocol, client_from_env

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("dreame-map-diag")


async def test_map_variants():
    # 1. Initialize client
    c = client_from_env()

    # Ensure tasshack is loaded
    _bootstrap_protocol(_REF_DEFAULT)

    logger.info(f"Connecting to Dreame cloud for user: {c._username}")
    ok = await c.connect()
    if not ok:
        logger.error("Connection failed!")
        return

    logger.info(f"Connected. DID: {c._did}")
    proto = c._protocol

    # 2. Get Object Name accurately
    obj_name = proto.object_name
    logger.info(f"Object Name: {obj_name}")

    # 3. Method A: get_device_file (MIoT File Bridge)
    # This is what c.get_map() does by default.
    logger.info("--- Testing Method A: get_device_file (File Bridge) ---")
    types_to_try = ["map", "0", obj_name]
    for t in types_to_try:
        try:
            logger.info(f"Trying get_device_file(filename='{obj_name}', file_type='{t}')...")
            # Sync call in executor to avoid blocking
            data = await asyncio.get_event_loop().run_in_executor(None, proto.get_device_file, obj_name, t)
            if data:
                logger.info(f"SUCCESS (A) with type='{t}': Got {len(data)} bytes")
                with open(f"D:/Dev/repos/temp/map_method_a_{t.replace('/', '_')}.bin", "wb") as f:
                    f.write(data)
                break
            else:
                logger.warning(f"Method A failed for type='{t}'")
        except Exception as e:
            logger.error(f"Method A Error: {e}")

    # 4. Method B: get_file_url (OSS Signed URL)
    logger.info("--- Testing Method B: get_file_url (OSS Signed URL) ---")
    # Tasshack's get_file_url expects object_name[1:] according to code
    obj_for_url = obj_name if not obj_name.startswith("/") else obj_name[1:]
    try:
        logger.info(f"Trying get_file_url('{obj_for_url}')...")
        url_data = await asyncio.get_event_loop().run_in_executor(None, proto.get_file_url, obj_for_url)
        if url_data:
            logger.info(f"URL Data received: {url_data}")
            # Extraction logic depends on what url_data is
            url = None
            if isinstance(url_data, dict):
                url = url_data.get("url") or url_data.get("fileUrl")
            elif isinstance(url_data, str):
                url = url_data

            if url:
                logger.info(f"Downloading from URL: {url[:100]}...")
                # Use tasshack's get_file or direct requests
                content = await asyncio.get_event_loop().run_in_executor(None, proto.get_file, url)
                if content:
                    logger.info(f"SUCCESS (B): Got {len(content)} bytes")
                    with open("D:/Dev/repos/temp/map_method_b.bin", "wb") as f:
                        f.write(content)
                else:
                    logger.warning("Method B: Download failed (get_file returned None)")
            else:
                logger.warning("Method B: No URL found in url_data")
        else:
            logger.warning("Method B failed (get_file_url returned None)")
    except Exception as e:
        logger.error(f"Method B Error: {e}")

    # 5. Method C: get_interim_file_url
    logger.info("--- Testing Method C: get_interim_file_url ---")
    try:
        url = await asyncio.get_event_loop().run_in_executor(None, proto.get_interim_file_url, obj_name)
        if url:
            logger.info(f"Interim URL received: {url[:100]}...")
            content = await asyncio.get_event_loop().run_in_executor(None, proto.get_file, url)
            if content:
                logger.info(f"SUCCESS (C): Got {len(content)} bytes")
                with open("D:/Dev/repos/temp/map_method_c.bin", "wb") as f:
                    f.write(content)
        else:
            logger.warning("Method C failed (get_interim_file_url returned None)")
    except Exception as e:
        logger.error(f"Method C Error: {e}")

    c.disconnect()


if __name__ == "__main__":
    # Ensure credentials are set (they are in the environment from start.ps1)
    asyncio.run(test_map_variants())
