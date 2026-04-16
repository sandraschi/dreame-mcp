import asyncio
import os
import logging
from dreame_mcp.client import DreameHomeClient

async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Use the known working IP and Null Token
    client = DreameHomeClient(
        ip="192.168.0.179",
        token="0" * 32
    )
    
    print("--- Connecting ---")
    ok = await client.connect()
    print(f"Connect OK: {ok}")
    
    if ok:
        print("--- Fetching Status ---")
        status = await client.get_status()
        print(f"Status: {status}")
        
        # We won't trigger a start_clean here to avoid disturbing the user,
        # but we can try a harmless 'find_robot' if it's mapped.
        print("--- Testing find_robot ---")
        res = await client.control("find_robot")
        print(f"Control Result: {res}")

if __name__ == "__main__":
    asyncio.run(main())
