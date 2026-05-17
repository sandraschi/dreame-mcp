"""Test Tasshack protocol directly."""
import logging, sys, os
logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)

sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), '..', 'src')))

from dreame_mcp.client import _bootstrap_protocol, _protocol_cls
from pathlib import Path

ref = Path(os.environ.get("DREAME_REF_PATH", "D:/Dev/repos/external/dreame-vacuum"))
_bootstrap_protocol(ref)
print(f"Protocol: {_protocol_cls}", flush=True)

proto = _protocol_cls(ip="192.168.0.178", token="0"*32, prefer_cloud=False)
print(f"Created. device={proto.device}", flush=True)

try:
    info = proto.connect(retry_count=1)
    print(f"connect() result: {info}", flush=True)
except Exception as e:
    print(f"connect() failed: {e}", flush=True)

print(f"connected={proto.connected}", flush=True)
