from __future__ import annotations

from mcp import StdioServerParameters

from google.adk.tools.mcp_tool import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
)

from app.config.settings import settings




filesystem_toolset = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx",
            args=[
                "-y",
                "@modelcontextprotocol/server-filesystem",
                settings.filesystem_allowed_dir,
            ],
        ),
        timeout=10.0,
    ),
    tool_filter=[
        "read_file",
        "read_multiple_files",
        "list_directory",
        "directory_tree",
        "search_files",
        "get_file_info",
        "write_file",
        "edit_file",
        "create_directory",
        "list_allowed_directories",
    ],
)

