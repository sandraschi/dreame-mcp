import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv, set_key

# Add the protocol path
REF_PATH = "D:/Dev/repos/external/dreame-vacuum"
sys.path.append(REF_PATH)
sys.path.append(os.path.join(REF_PATH, "custom_components", "dreame_vacuum"))

# Import Tasshack protocol components
try:
    from dreame.protocol import DreameVacuumProtocol
except ImportError:
    print("FATAL: Could not import dreame protocol. check DREAME_REF_PATH.")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cloud-fix")

def main():
    load_dotenv()
    user = os.environ.get("DREAME_USER")
    pwd = os.environ.get("DREAME_PASSWORD")
    country = os.environ.get("DREAME_COUNTRY", "eu")
    
    if not user or not pwd:
        print("ERROR: DREAME_USER or DREAME_PASSWORD missing from .env")
        return

    print(f"--- Logging into DreameHome as {user} ({country}) ---")
    
    # We use a dummy IP/Token for login
    proto = DreameVacuumProtocol(
        username=user,
        password=pwd,
        country=country,
        prefer_cloud=True
    )
    
    ok = proto.cloud.login()
    if not ok:
        print("FAILED: Cloud login failed. check credentials.")
        return
    
    print("SUCCESS: Logged in!")
    devices = proto.cloud.get_devices()
    
    if not devices:
        print("FAILED: No devices found in cloud account.")
        return
    
    # We take the first device (usually only one D20 Pro Plus)
    target = devices[0]
    new_ip = target.get("localip")
    new_token = target.get("token")
    new_did = str(target.get("did"))
    name = target.get("name", "Unknown")
    
    print(f"\n--- Found Robot: {name} ---")
    print(f"New IP:    {new_ip}")
    print(f"New Token: {new_token}")
    print(f"DID:       {new_did}")
    
    # Update .env
    env_file = ".env"
    print(f"\nUpdating {env_file}...")
    set_key(env_file, "DREAME_IP", new_ip)
    set_key(env_file, "DREAME_TOKEN", new_token)
    set_key(env_file, "DREAME_DID", new_did)
    
    print("\n[DONE] .env updated. Now try running the verification script.")

if __name__ == "__main__":
    main()
