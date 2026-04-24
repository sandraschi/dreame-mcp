
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path("D:/Dev/repos/dreame-mcp/src")))

from dreame_mcp.portmanteau import fetch_status_data, fetch_map_data, dreame_tool

async def test_refactor():
    print("Testing refactor (Structured Data vs Markdown)...")
    
    # In stub mode (client=None)
    data = await fetch_status_data(None)
    print(f"fetch_status_data(None) type: {type(data)}")
    print(f"fetch_status_data(None) success: {data.get('success')}")
    
    if not isinstance(data, dict):
        print("FAIL: fetch_status_data did not return a dict")
        return

    md = await dreame_tool(operation="status")
    print(f"dreame_tool(operation='status') type: {type(md)}")
    if not isinstance(md, str):
        print("FAIL: dreame_tool did not return a str")
        return
    
    print("--- Markdown Preview ---")
    print(md[:100] + "...")
    print("--- End Preview ---")
    
    print("SUCCESS: Refactor verified. API gets dict, AI gets Markdown.")

if __name__ == "__main__":
    asyncio.run(test_refactor())
