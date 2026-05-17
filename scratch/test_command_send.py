"""Test sending commands via DreameHome cloud."""
import logging
import sys
import os
from pathlib import Path

logging.basicConfig(level=logging.DEBUG, stream=sys.stderr, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from dotenv import load_dotenv
load_dotenv()

import dreame_mcp.client as mc

ref_path = Path(os.environ.get("DREAME_REF_PATH", "D:/Dev/repos/tasshack_dreame_vacuum_ref"))
mc._bootstrap_protocol(ref_path)

username = os.environ.get("DREAME_USER", "").strip()
password = os.environ.get("DREAME_PASSWORD", "").strip()
country = os.environ.get("DREAME_COUNTRY", "eu").strip()
did = os.environ.get("DREAME_DID", "2045852486").strip()

cloud = mc._cloud_cls(
    username=username,
    password=password,
    country=country,
    account_type="dreame",
    auth_key=None,
    did=did,
)
ok = cloud.login()
print(f"Cloud login: {ok}", flush=True)

# Try get_properties
print(f"\n--- get_properties ---", flush=True)
result = cloud.send("get_properties", [
    {"did": did, "siid": 3, "piid": 1},
])
print(f"get_properties result: {result}", flush=True)

# Try miIO.info
print(f"\n--- miIO.info ---", flush=True)
try:
    result = cloud.send("miIO.info", {})
    print(f"miIO.info result: {result}", flush=True)
except Exception as e:
    print(f"miIO.info error: {e}", flush=True)

# Try action
print(f"\n--- action(start_clean) ---", flush=True)
try:
    result = cloud.send("action", {
        "did": did,
        "siid": 2,
        "aiid": 1,
        "in": [],
    })
    print(f"action result: {result}", flush=True)
except Exception as e:
    print(f"action error: {e}", flush=True)

# Try get_properties with different approach (method as MIoT)
print(f"\n--- get_properties (miot) ---", flush=True)
try:
    result = cloud.send("get_properties", [
        {"did": did, "siid": 3, "piid": 1},
    ])
    print(f"result: {result}", flush=True)
except Exception as e:
    print(f"error: {e}", flush=True)

# Check device connectivity via get_device_info
print(f"\n--- connect + get_device_info ---", flush=True)
try:
    info = cloud.connect()
    print(f"connect result: {info}", flush=True)
except Exception as e:
    import traceback
    print(f"connect error: {e}", flush=True)
    traceback.print_exc()
