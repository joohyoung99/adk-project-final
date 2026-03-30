from __future__ import annotations

from typing import Optional

from google.adk.agents.callback_context import CallbackContext
from google.genai import types

# TODO : before_agent_callback, before_model_callback, after_tool_callback, after_model_callback 등 필요한 콜백 추가

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
    "실시간",
    "농협",
    "nh",
    "didim",
    "디딤",
    "캠페인",
    "notion",
    "rag",
    "internal",
    "기술",
    "요약",
    "비교",
    "외부",
)

SPECULATION_KEYWORDS = (
    "추정",
    "아마",
    "가능성이",
    "예상",
    "보입니다",
)

GROUNDING_NOTICE = "※ 위 답변은 Vertex RAG corpus 검색 결과를 기반으로 작성되었습니다."
SUMMARY_SECTION_KEYWORDS = ("핵심", "요약", "추천", "다음 액션")
TECH_COMPARE_KEYWORDS = ("비교", "장점", "단점", "추천", "근거")


def _extract_user_text(callback_context: CallbackContext) -> str:
    """현재 요청에서 사용자 텍스트를 추출한다."""
    content = getattr(callback_context, "user_content", None)
    if not content or not getattr(content, "parts", None):
        return ""

    texts = [part.text for part in content.parts if getattr(part, "text", None)]
    return " ".join(texts).strip().lower()


def _extract_content_text(content: types.Content | None) -> str:
    """Content 객체에서 텍스트만 추출한다."""
    if not content or not getattr(content, "parts", None):
        return ""

    texts = [part.text for part in content.parts if getattr(part, "text", None)]
    return "\n".join(texts).strip()


def _state_get(callback_context: CallbackContext, key: str, default: str = "") -> str:
    """context.state에서 문자열 값을 안전하게 읽는다."""
    state = getattr(callback_context, "state", None)
    if state is None:
        return default

    if hasattr(state, "get"):
        value = state.get(key, default)
    else:
        try:
            value = state[key]
        except Exception:
            return default

    if value is None:
        return default
    return str(value).strip()


def _has_state_value(callback_context: CallbackContext, key: str) -> bool:
    """context.state에 의미 있는 값이 있는지 확인한다."""
    return bool(_state_get(callback_context, key))


def _build_model_content(text: str) -> types.Content:
    """콜백에서 즉시 반환할 모델 텍스트 응답을 만든다."""
    return types.Content(role="model", parts=[types.Part(text=text)])


def before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """사내 문서 관련 질문이 아니면 에이전트 실행 전에 차단한다."""
    user_text = _extract_user_text(callback_context)
    state = getattr(callback_context, "state", None)
    if state is not None and user_text:
        state["user_query"] = user_text
    if any(keyword in user_text for keyword in INTERNAL_DOC_KEYWORDS):
        return None

    return _build_model_content(
        "저는 최신 기술과 사내 보유 기술의 비교 분석, 사내 문서, 사내 프로젝트, 내부 기술 자료와 관련된 질문에만 답변할 수 있습니다."
         "사내 문서를 기준으로 다시 질문해 주세요."
    )


def _validate_rag_response(callback_context: CallbackContext) -> types.Content | None:
    """RAG 결과와 답변을 검증하고 필요하면 응답을 교정한다."""
    answer = _state_get(callback_context, "answer")
    rag_result = _state_get(callback_context, "rag_result")
    rag_rewrite = _state_get(callback_context, "rag_rewrite")

    if not answer:
        answer = _extract_content_text(getattr(callback_context, "user_content", None))

    if not rag_result:
        return _build_model_content(
            "관련 사내 문서를 찾지 못해 답변을 생성할 수 없습니다. "
            "검색 범위를 좁히거나 문서명, 프로젝트명, 기간을 포함해 다시 질문해 주세요."
        )

    if any(keyword in answer for keyword in SPECULATION_KEYWORDS):
        return _build_model_content(
            "현재 생성된 답변에는 문서 근거 없이 추측성 표현이 포함되어 있어 반환하지 않습니다. "
            "사내 문서 기준으로만 다시 질의해 주세요."
        )

    if GROUNDING_NOTICE not in answer:
        answer = f"{answer.rstrip()}\n\n{GROUNDING_NOTICE}"

    if rag_rewrite and rag_rewrite not in answer and "제공된 문서 기준으로는 확인되지 않는다" not in answer:
        answer = (
            f"{answer.rstrip()}\n\n"
        )

    return _build_model_content(answer)


def _validate_summary_response(callback_context: CallbackContext) -> types.Content | None:
    """문서 요약 결과가 최소 구조를 갖췄는지 검증한다."""
    summary = _state_get(callback_context, "summary")

    if not summary:
        return _build_model_content(
            "문서 요약 결과가 비어 있어 응답을 반환할 수 없습니다. "
            "요약 대상 문서나 검색 결과를 다시 확인해 주세요."
        )

    if not any(keyword in summary for keyword in SUMMARY_SECTION_KEYWORDS):
        summary = f"핵심 요약\n{summary.strip()}"

    return _build_model_content(summary)


def _validate_tech_compare_response(callback_context: CallbackContext) -> types.Content | None:
    """기술 비교 결과가 비교/추천 형식을 갖추는지 검증한다."""
    compare_result = _state_get(callback_context, "parallel_answer")
    
    if not compare_result:
        return _build_model_content(
            "기술 비교 결과가 비어 있어 응답을 생성할 수 없습니다. "
            "비교 대상 기술명이나 문서 범위를 더 구체적으로 지정해 주세요."
        )

    if not any(keyword in compare_result for keyword in TECH_COMPARE_KEYWORDS):
        compare_result = (
            f"기술 비교 요약\n{compare_result.strip()}\n\n"
            "추천: 제공된 사내 문서 기준으로 추가 비교 근거를 보완해 주세요."
        )

    return _build_model_content(compare_result)


def after_agent_callback(callback_context: CallbackContext) -> types.Content | None:
    """state와 agent 정보를 보고 도메인별 후처리 검증으로 분기한다."""
    agent_name = getattr(callback_context, "agent_name", "")

    if agent_name == "RagAnswerAgent" or _has_state_value(callback_context, "rag_result"):
        return _validate_rag_response(callback_context)

    if agent_name == "SummaryOnlyAgent" or _has_state_value(callback_context, "summary"):
        return _validate_summary_response(callback_context)

    if agent_name == "ParallelAnswerAgent" or _has_state_value(callback_context, "parallel_answer"):
        return _validate_tech_compare_response(callback_context)

    return None
