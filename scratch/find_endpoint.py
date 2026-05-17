"""Find the correct DreameHome command endpoint."""
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

# Get device info first - use cloud's own _api_call for testing
import requests

# The auth headers the protocol uses
headers = {
    "Accept": "*/*",
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept-Language": "en-US;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "User-Agent": cloud._strings[3],
    "Authorization": cloud._strings[5],
    "Tenant-Id": cloud._ti if cloud._ti else cloud._strings[6],
    "Content-Type": "application/json",
    "Dreame-Auth": cloud._key,
}

base = f"https://eu.iot.dreame.tech:13267"

# Try different paths for sendCommand
paths = [
    "dreame-user-iot/device/sendCommand",
    "dreame-user-iot/iotdevice/sendCommand",
    "dreame-user-iot/iotdevice/command",
    "dreame-user-iot/iotuserbind/device/sendCommand",
    "dreame-user-iot/iotstatus/device/sendCommand",
    "dreame-user-iot/iotuserdata/device/sendCommand",
    "dreame-iot-com/device/sendCommand",
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

for p in paths:
    url = f"{base}/{p}"
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=5)
        txt = r.text[:150]
        print(f"  {p}: {r.status_code} {txt}", flush=True)
    except Exception as e:
        print(f"  {p}: ERROR {e}", flush=True)
