
import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path("D:/Dev/repos/dreame-mcp/src")))

# Mock a .env file content
env_path = Path("D:/Dev/repos/dreame-mcp/.env.test")
env_path.write_text(
    "DREAME_IP=192.168.0.100\n"
    "DREAME_TOKEN=1234567890abcdef1234567890abcdef\n"
)

try:
    from dreame_mcp.client import client_from_env

    # We need to monkeypatch dotenv to find our test file or just rename it
    # But since client_from_env calls load_dotenv(), it will look for .env
    # For this test, let's temporarily backup .env and use our test one
    real_env = Path("D:/Dev/repos/dreame-mcp/.env")
    backup = Path("D:/Dev/repos/dreame-mcp/.env.bak")
    
    if real_env.exists():
        real_env.rename(backup)
    
    env_path.rename(real_env)

    print("Testing .env loading...")
    client = client_from_env()

    if client:
        print(f"SUCCESS: Client initialized with IP: {client._ip}")
        if client._ip == "192.168.0.100":
            print("Verified: Correct IP loaded.")
        else:
            print(f"FAIL: Wrong IP loaded: {client._ip}")
    else:
        print("FAIL: Client is None (Stub Mode)")

finally:
    # Cleanup
    if real_env.exists():
        real_env.unlink()
    if backup.exists():
        backup.rename(real_env)
    if env_path.exists():
        env_path.unlink()

if __name__ == "__main__":
    pass
