"""Probe DreameHome API endpoints to find the working command path."""
import logging
import sys
import os, json
from pathlib import Path

logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

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

# Get device info first to populate _host
info = cloud.get_device_info()
print(f"Device info obtained", flush=True)
print(f"  host (from strings[9]): {cloud._host}", flush=True)

# Try send via the MQTT-style path (send_async just queues, but we can check the endpoint)
# Try direct REST probe for different command endpoints
import requests

def try_endpoint(path, payload=None):
    url = f"https://eu.iot.dreame.tech:13267{path}"
    headers = {
        "Content-Type": "application/json",
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=5)
        print(f"  {path}: {r.status_code} {r.text[:200]}", flush=True)
    except Exception as e:
        print(f"  {path}: ERROR {e}", flush=True)

# Probe endpoints
endpoints = [
    "/dreame-iot-com/device/sendCommand",
    "/dreame-iot-com/iotdevice/command",
    "/dreame-iot-com/device/command",
    "/dreame-user-iot/iotdevice/sendCommand",
    "/dreame-user-iot/iotdevice/command",
    "/dreame-user-iot/device/command",
    "/dreame-user-iot/device/sendCommand",
    "/dreame-iot-com/v2/device/sendCommand",
    "/dreame-iot-com/device/miotCommand",
]

payload = {
    "did": did,
    "id": 1,
    "data": {
        "did": did,
        "id": 1,
        "method": "get_properties",
        "params": [{"did": did, "siid": 3, "piid": 1}],
    },
}

for ep in endpoints:
    try_endpoint(ep, payload)

# Also try without auth headers (some endpoints might use different auth)
# Try with the session cookie
print(f"\nTrying with session auth:", flush=True)
url = f"https://eu.iot.dreame.tech:13267/dreame-iot-com/device/sendCommand"
r = cloud._session.post(url, json=payload, timeout=5)
print(f"  (with session): {r.status_code} {r.text[:200]}", flush=True)
