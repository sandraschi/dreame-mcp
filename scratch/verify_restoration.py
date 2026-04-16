
import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path("D:/Dev/repos/dreame-mcp/src")))

from dreame_mcp.client import client_from_env

def test_bootstrap():
    print("Testing bootstrap and client initialization...")
    
    # Mock some env vars if missing to see if client constructs
    if not os.environ.get("DREAME_IP"):
        os.environ["DREAME_IP"] = "192.168.1.100"
        os.environ["DREAME_TOKEN"] = "abcdef1234567890"
        os.environ["DREAME_REF_PATH"] = "D:/Dev/repos/external/dreame-vacuum"
    
    client = client_from_env()
    if not client:
        print("FAIL: client_from_env returned None")
        return
    
    print(f"Client created: IP={client._ip}, Ref={client._ref_path}")
    
    # Try to bootstrap (this will fail if the path is wrong, which is a good test)
    try:
        from dreame_mcp.client import _bootstrap_protocol
        _bootstrap_protocol(client._ref_path)
        print("SUCCESS: Protocol bootstrapped OK")
    except Exception as e:
        print(f"FAIL: Bootstrap failed: {e}")

if __name__ == "__main__":
    test_bootstrap()
