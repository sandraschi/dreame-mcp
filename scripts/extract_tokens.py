
import asyncio
import os
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.append(str(Path("D:/Dev/repos/dreame-mcp/src")))

from dreame_mcp.client import client_from_env

# Disable noise
logging.getLogger("dreame-mcp").setLevel(logging.INFO)

async def extract():
    print("--- Dreame Token Extractor ---")
    client = client_from_env()
    
    if not client or not client._username or not client._password:
        print("\n[ERROR] DREAME_USER and DREAME_PASSWORD must be set in your .env file to extract tokens.")
        return

    print(f"Logging in as {client._username} ({client._country})...")
    
    # We use the internal connect logic which bootstraps the protocol
    ok = await client.connect()
    if not ok:
        print("[ERROR] Login failed. Check your credentials and country (eu/us/cn).")
        return

    print("\nSUCCESS! Discovered devices:\n")
    print("-" * 60)
    
    # Access the raw protocol cloud records
    if client._protocol and client._protocol.cloud:
        devices_raw = client._protocol.cloud.get_devices()
        
        # SOTA-Hardened Discovery: Handle both flat lists and paged record structures
        records = []
        if isinstance(devices_raw, list):
            records = devices_raw
        elif isinstance(devices_raw, dict):
            records = devices_raw.get("page", {}).get("records", [])
            
        if not records:
            print("[INFO] No devices found on this account.")
            return
        
        for i, dev in enumerate(records):
            name = dev.get("name", "Unknown")
            model = dev.get("model", "Unknown")
            did = str(dev.get("did", ""))
            ip = dev.get("localip", "Unknown")
            token = dev.get("token", "Unknown")
            online = "[ONLINE]" if dev.get("is_online") else "[OFFLINE]"
            
            print(f"Device #{i+1}: {name} {online}")
            print(f"  Model: {model}")
            print(f"  IP   : {ip}")
            print(f"  Token: {token}")
            print(f"  DID  : {did}")
            print("-" * 60)
            
        print("\nACTION: Copy the 'IP' and 'Token' into your .env file.")
        print("Note: If the IP is 'Unknown', check the DreameHome app for the robot's local address.")
    else:
        print("[ERROR] Cloud protocol not initialized.")

if __name__ == "__main__":
    asyncio.run(extract())
