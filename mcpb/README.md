# dreame-mcp (MCPB Bundle)

FastMCP 3.2.0 MCP server and webapp for Dreame robot vacuums via DreameHome cloud

## Usage

Add to \claude_desktop_config.json\:
\\\json
{
  "mcpServers": {
    "dreame-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "\D:\Dev\repos", "python", "-m", "dreame_mcp"],
      "env": { "PYTHONPATH": "\D:\Dev\repos/src" }
    }
  }
}
\\\

## Tools

- **dreame_tool**: dreame_tool

## Requirements

- Python 3.12+
- uv
