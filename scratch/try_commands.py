"""Try different command structures for DreameHome API."""
import logging, sys, os, json
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

import requests

# Standard auth headers that the protocol uses
headers = {
    "Accept": "*/*",
    "Content-Type": "application/json",
    "Accept-Language": "en-US;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "User-Agent": cloud._strings[3],
    "Authorization": cloud._strings[5],
    "Tenant-Id": cloud._ti if cloud._ti else cloud._strings[6],
    "Dreame-Auth": cloud._key,
}

base = "https://eu.iot.dreame.tech:13267"

test_cases = [
    # Different payload formats at user-iot/iotdevice/sendCommand
    {
        "path": "dreame-user-iot/iotdevice/sendCommand",
        "payload": {"did": did, "id": 1, "method": "action", "params": {"siid": 2, "aiid": 1, "in": []}},
    },
    {
        "path": "dreame-user-iot/iotdevice/action",
        "payload": {"did": did, "siid": 2, "aiid": 1, "in": []},
    },
    {
        "path": "dreame-user-iot/iotdevice/sendCommand",
        "payload": {"did": did, "method": "action", "param": json.dumps({"siid": 2, "aiid": 1, "in": []})},
    },
    # Try with get_properties in different formats
    {
        "path": "dreame-user-iot/iotdevice/getProperties",
        "payload": {"did": did, "siid": 3, "piid": 1},
    },
    # Flat structure
    {
        "path": "dreame-user-iot/iotdevice/sendCommand",
        "payload": {"did": did, "siid": 3, "piid": 1},
    },
    # Via the userbind path
    {
        "path": "dreame-user-iot/iotuserbind/device/action",
        "payload": {"did": did, "siid": 2, "aiid": 1, "in": []},
    },
    # Try string format
    {
        "path": "dreame-user-iot/iotdevice/sendCommand",
        "payload": json.dumps({"did": did, "data": {"method": "action", "params": {"siid": 2, "aiid": 1, "in": []}}}),
    },
]

for tc in test_cases:
    url = f"{base}/{tc['path']}"
    try:
        r = requests.post(url, json=tc['payload'], headers=headers, timeout=10)
        txt = r.text[:200]
        print(f"POST /{tc['path']}: {r.status_code} {txt}", flush=True)
    except Exception as e:
        print(f"POST /{tc['path']}: ERROR {e}", flush=True)
