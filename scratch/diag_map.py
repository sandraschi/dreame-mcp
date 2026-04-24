import asyncio
import os
import sys
from dreame_mcp.client import client_from_env

async def main():
    client = client_from_env()
    if not client:
        print("No client found (check ENV)")
        return
    
    print(f"Connecting to {client._user}...")
    ok = await client.connect()
    if not ok:
        print("Connect failed")
        return
    
    print("Fetching map...")
    res = await client.get_map()
    if res.get("success"):
        print("Success! Map received.")
        print(f"Object: {res.get('object_name')}")
        md = res.get("map_data", {})
        print(f"Rooms: {md.get('rooms')}")
        print(f"Robot: {md.get('robot_position')}")
        print(f"Path points: {len(md.get('path', []))}")
        print(f"Walls: {len(md.get('virtual_walls', []))}")
    else:
        print(f"Map fetch failed: {res.get('error')}")

if __name__ == "__main__":
    # Add src to path
    sys.path.append(os.path.join(os.getcwd(), "src"))
    asyncio.run(main())
