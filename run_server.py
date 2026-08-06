"""PyInstaller entry point — dual transport.

MCP_PORT / PORT / DREAME_MCP_PORT set  -> HTTP (uvicorn on 127.0.0.1:{port})
otherwise                               -> stdio (Claude Desktop etc.)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn

from dreame_mcp.server import app

port = (
    os.environ.get("MCP_PORT")
    or os.environ.get("PORT")
    or os.environ.get("DREAME_MCP_PORT")
)
if port:
    host = os.environ.get("MCP_HOST", "127.0.0.1")
    config = uvicorn.Config(app, host=host, port=int(port), log_level="info")
    uvicorn.Server(config).run()
else:
    from fastmcp.cli import run_stdio

    from dreame_mcp.server import mcp

    run_stdio(mcp)
