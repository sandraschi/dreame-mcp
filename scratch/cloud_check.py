"""Test cloud login with detailed debug."""
import logging, sys, os, json
logging.basicConfig(level=logging.DEBUG, stream=sys.stderr, force=True)
sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), '..', 'src')))
from dotenv import load_dotenv
load_dotenv()
from dreame_mcp.client import _bootstrap_protocol, _protocol_cls
from pathlib import Path

ref = Path(os.environ.get("DREAME_REF_PATH", "D:/Dev/repos/external/dreame-vacuum"))
_bootstrap_protocol(ref)

proto = _protocol_cls(
    username=os.environ["DREAME_USER"],
    password=os.environ["DREAME_PASSWORD"],
    country=os.environ.get("DREAME_COUNTRY", "eu"),
)
print(f"Cloud protocol: {proto.cloud}", flush=True)
if proto.cloud:
    ok = proto.cloud.login()
    print(f"Cloud login: {ok}", flush=True)
    print(f"auth_failed: {getattr(proto.cloud, 'auth_failed', '?')}", flush=True)
    print(f"logged_in: {getattr(proto.cloud, 'logged_in', '?')}", flush=True)
    print(f"connected: {getattr(proto.cloud, 'connected', '?')}", flush=True)
    if ok:
        devices = proto.cloud.get_devices()
        print(f"Devices ({len(devices) if devices else 0}):")
        if devices:
            for d in devices:
                print(json.dumps(d, indent=2, default=str))
    else:
        print("Trying to get any stored info...")
        print(f"auth_key: {getattr(proto.cloud, 'auth_key', 'N/A')}")
        print(f"_did: {getattr(proto.cloud, '_did', 'N/A')}")
