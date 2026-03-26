from __future__ import annotations

import json
from typing import Any

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext


def _compact(value: Any, limit: int = 700) -> str:
    """로그 출력용으로 객체를 짧은 문자열로 변환한다."""
    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
    except TypeError:
        text = repr(value)
    if len(text) <= limit:
        return text
    return f"{text[:limit]}...<truncated>"

def before_tool_callback(tool: BaseTool, args: dict[str, Any], tool_context: ToolContext) -> None:
    """도구 실행 직전에 에이전트와 인자를 로그로 남긴다."""
    print(f"[TOOL CALL] agent={tool_context.agent_name} tool={tool.name}")
    print(f"[TOOL ARGS] {_compact(args)}")
    return None
