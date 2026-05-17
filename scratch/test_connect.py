"""Test the DreameHomeClient connection directly."""
import logging
import sys
import os
from pathlib import Path

logging.basicConfig(level=logging.DEBUG, stream=sys.stderr, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dotenv import load_dotenv
load_dotenv()

from dreame_mcp.client import DreameHomeClient, _bootstrap_protocol, _protocol_cls
from dreame_mcp.client import _REF_DEFAULT

ref_raw = os.environ.get("DREAME_REF_PATH", "").strip()
ref_path = Path(ref_raw) if ref_raw else _REF_DEFAULT
print(f"Ref path: {ref_path}", flush=True)

# Bootstrap protocol first
try:
    _bootstrap_protocol(ref_path)
    print(f"Bootstrap OK, protocol class: {_protocol_cls}", flush=True)
except Exception as e:
    print(f"Bootstrap FAILED: {e}", flush=True)
    sys.exit(1)

# Now try creating the protocol
ip = os.environ.get("DREAME_IP", "").strip()
user = os.environ.get("DREAME_USER", "").strip()
pwd = os.environ.get("DREAME_PASSWORD", "").strip()
token = os.environ.get("DREAME_TOKEN", "").strip() or "0" * 32
country = os.environ.get("DREAME_COUNTRY", "eu").strip()

print(f"IP: {ip}, user: {user[:4]}..., token_len: {len(token)}, country: {country}", flush=True)

protocol = _protocol_cls(
    ip=ip,
    token=token,
    username=user,
    password=pwd,
    country=country,
    auth_key=None,
    device_id=None,
    prefer_cloud=False,
)
print(f"Protocol created. connected={protocol.connected}", flush=True)

# Try cloud login
if user and pwd and protocol.cloud:
    print("Attempting cloud login...", flush=True)
    ok = protocol.cloud.login()
    print(f"Cloud login: {ok}", flush=True)
    if ok:
        devices = protocol.cloud.get_devices()
        print(f"Devices: {devices}", flush=True)
    else:
        print("Cloud login failed", flush=True)
        c = protocol.cloud
        print(f"  auth_failed: {getattr(c, 'auth_failed', 'N/A')}", flush=True)
        print(f"  auth_key: {getattr(c, 'auth_key', 'N/A')}", flush=True)
        print(f"  _did: {getattr(c, '_did', 'N/A')}", flush=True)
else:
    print("No cloud credentials, skipping cloud login", flush=True)

print(f"Final: connected={protocol.connected}, device={getattr(protocol, 'device', None)}", flush=True)
