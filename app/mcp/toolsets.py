from __future__ import annotations

from mcp import StdioServerParameters

from google.adk.tools.mcp_tool import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
)

from app.config.settings import settings




github_mcp_toolset = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=settings.github_mcp_server_path,
            args=["stdio"],
            env={
                "GITHUB_PERSONAL_ACCESS_TOKEN": settings.github_personal_access_token,
                "GITHUB_TOOLSETS": "repos,issues,pull_requests,users",
                "GITHUB_READ_ONLY": "1",
            },
        ),
        timeout=20.0,
    ),
)
