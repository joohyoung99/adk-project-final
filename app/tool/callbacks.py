from __future__ import annotations

from app.services.runtime_logging import before_tool_callback



# TODO : before_agent_callback, before_model_callback , after_tool_callback , after_model_callback 등 필요한 콜백 추가


def tool_callbacks() -> dict[str, object]:
    """에이전트 생성 시 재사용할 공통 tool callback을 반환한다."""
    return {
        "before_tool_callback": before_tool_callback,
    }
