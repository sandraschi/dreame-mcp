import os
import logging
import asyncio
from dotenv import load_dotenv
from dreame_mcp.client import client_from_env

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("diagnostic")

async def main():
    load_dotenv()
    
    # We use the client_from_env to get the session
    client = client_from_env()
    
    try:
        # Initialize connection (includes cloud login)
        await client.connect()
        
        if not client._protocol or not client._protocol.cloud:
            print("[ERROR] Cloud protocol not initialized. Check your .env (DREAME_USER/PASSWORD/COUNTRY)")
            return
            
        print("\n--- Dreame Cloud Diagnostics ---")
        devices = client._protocol.cloud.get_devices()
        print(f"Discovered {len(devices) if devices else 0} devices.")
        
        if devices:
            for i, d in enumerate(devices):
                print(f"\n[Device {i}]")
                print(f"  Name: {d.get('name')}")
                print(f"  DID:  {d.get('did')}")
                print(f"  IP:   {d.get('localip')}")
                print(f"  MAC:  {d.get('mac')}")
                print(f"  Token: {'***' + d.get('token')[-4:] if d.get('token') else 'MISSING'}")
                print(f"  Online: {d.get('is_online')}")
                
    except Exception as e:
        print(f"[ERROR] Error during diagnostics: {e}")
    finally:
        # disconnect is async in client.py
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
