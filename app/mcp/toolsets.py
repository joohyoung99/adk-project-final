from __future__ import annotations

from mcp import StdioServerParameters

from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
)

from app.config.settings import settings


def _split_github_repository(repository: str) -> tuple[str, str]:
    normalized = repository.strip().strip("/")
    if not normalized or "/" not in normalized:
        return "", ""

    owner, repo = normalized.split("/", 1)
    return owner.strip(), repo.strip()


github_default_owner, github_default_repo = _split_github_repository(
    settings.github_default_repository
)


github_mcp_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=settings.github_mcp_server_path,
            args=["stdio"],
            env={
                "GITHUB_PERSONAL_ACCESS_TOKEN": settings.github_personal_access_token,
                "GITHUB_TOOLSETS": "repos,issues,pull_requests,users",
                "GITHUB_READ_ONLY": "1",
                "GITHUB_DEFAULT_REPOSITORY": settings.github_default_repository,
                "GITHUB_DEFAULT_OWNER": github_default_owner,
                "GITHUB_DEFAULT_REPO": github_default_repo,
            },
        ),
        timeout=20.0,
    ),
)
