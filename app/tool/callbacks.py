from __future__ import annotations

from google.adk.agents.context import Context
from google.genai import types

from app.services.runtime_logging import before_tool_callback



# TODO : before_agent_callback, before_model_callback , after_tool_callback , after_model_callback 등 필요한 콜백 추가

INTERNAL_DOC_KEYWORDS = (
    "사내",
    "문서",
    "내부",
    "프로젝트",
    "회의록",
    "기술사례",
    "구축사례",
    "제안서",
    "보고서",
    "고객사",
    "캠페인",
    "notion",
    "rag",
    "internal",
)


def _extract_user_text(context: Context) -> str:
    """현재 요청에서 사용자 텍스트를 추출한다."""
    content = getattr(context, "user_content", None)
    if not content or not getattr(content, "parts", None):
        return ""

    texts = [part.text for part in content.parts if getattr(part, "text", None)]
    return " ".join(texts).strip().lower()


def before_agent_callback(context: Context) -> types.Content | None:
    """사내 문서 관련 질문이 아니면 에이전트 실행 전에 차단한다."""
    user_text = _extract_user_text(context)
    if any(keyword in user_text for keyword in INTERNAL_DOC_KEYWORDS):
        return None

    return types.Content(
        role="model",
        parts=[
            types.Part(
                text=(
                    "사내 문서, 사내 프로젝트, 내부 기술 자료와 관련된 질문만 답변할 수 있습니다. "
                    "사내 문서 기준으로 다시 질문해 주세요."
                )
            )
        ],
    )


def tool_callbacks() -> dict[str, object]:
    """에이전트 생성 시 재사용할 공통 callback 묶음을 반환한다."""
    return {
        "before_agent_callback": before_agent_callback,
        "before_tool_callback": before_tool_callback,
    }
