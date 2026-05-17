"""Test DreameHome cloud login with DreameVacuumDreameHomeCloudProtocol."""
import logging
import sys
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from dotenv import load_dotenv

load_dotenv()

import dreame_mcp.client as mc

ref_path = Path(os.environ.get("DREAME_REF_PATH", "D:/Dev/repos/tasshack_dreame_vacuum_ref"))
print(f"Ref: {ref_path}", flush=True)

mc._bootstrap_protocol(ref_path)

print(f"_cloud_cls: {mc._cloud_cls}", flush=True)
print(f"_protocol_cls: {mc._protocol_cls}", flush=True)

if mc._cloud_cls is None:
    print("ERROR: _cloud_cls is None", flush=True)
    sys.exit(1)

username = os.environ.get("DREAME_USER", "").strip()
password = os.environ.get("DREAME_PASSWORD", "").strip()
country = os.environ.get("DREAME_COUNTRY", "eu").strip()
did = os.environ.get("DREAME_DID", "").strip() or None

print(f"Attempting cloud login with {username} (country={country})", flush=True)

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
if ok:
    key = cloud.auth_key
    print(f"Logged in! auth_key={key[:40]}..." if key else "No auth_key", flush=True)
    devices = cloud.get_devices()
    if devices:
        records = devices.get("page", {}).get("records", [])
        print(f"Devices found: {len(records)}", flush=True)
        for d in records:
            di = d.get("did", "")
            nm = d.get("name", "?")
            md = d.get("model", "?")
            print(f"  DID={di} name={nm} model={md}", flush=True)
    else:
        print("No devices returned", flush=True)

    # Try getting status
    if did:
        result = cloud.send("get_properties", [
            {"did": did, "siid": 3, "piid": 1},
            {"did": did, "siid": 2, "piid": 1},
        ])
        print(f"Status result: {result}", flush=True)
else:
    print(f"Login failed. auth_failed: {cloud.auth_failed}", flush=True)
