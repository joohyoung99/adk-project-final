from __future__ import annotations

import re
from typing import Any, Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools import BaseTool, ToolContext
from google.genai import types


# =========================================================
# 정책 상수
# =========================================================

INTERNAL_DOC_KEYWORDS = (
    "사내 문서",
    "내부 문서",
    "사내 자료",
    "내부 자료",
    "사내 프로젝트",
    "내부 프로젝트",
    "회의록",
    "기술사례",
    "구축사례",
    "제안서",
    "보고서",
    "고객사",
    "notion",
    "didim",
    "디딤",
    "nh",
    "농협",
    "rag",
    "internal",
)

GITHUB_KEYWORDS = (
    "github",
    "깃헙",
    "저장소",
    "repo",
    "repository",
    "브랜치",
    "branch",
    "커밋",
    "commit",
    "pr",
    "pull request",
    "이슈",
    "issue",
    "workflow",
    "action",
    "actions",
    "코드",
    "소스",
    "파일",
)

FOLLOW_UP_REFERENTIAL_KEYWORDS = (
    "그거",
    "그 문서",
    "그 자료",
    "그 내용",
    "그 결과",
    "이 문서",
    "이 자료",
    "이 내용",
    "이 결과",
    "위 내용",
    "위 결과",
    "방금",
    "앞서",
    "이어서",
    "계속",
    "추가로",
    "그럼",
    "그러면",
    "아까",
    "방금 문서 기준",
    "위 문서 기준",
    "방금 github 기준",
    "방금 깃헙 기준",
)

FOLLOW_UP_INTENT_KEYWORDS = (
    "더 자세히",
    "자세히",
    "정리",
    "요약",
    "표로",
    "근거",
    "원인",
    "리스크",
    "장단점",
    "비교",
    "추천",
    "다음 액션",
    "왜",
    "어떻게",
)

INTERNAL_CONTEXT_STATE_KEYS = (
    "rag_result",
    "rag_rewrite",
    "answer",
    "summary",
    "parallel_answer",
    "parallel_merged_result",
    "parallel_rag_result",
)

GITHUB_CONTEXT_STATE_KEYS = (
    "github_rewrite",
    "github_search_result",
    "github_answer",
)

SUMMARY_SECTION_KEYWORDS = ("핵심", "요약", "추천", "다음 액션")
TECH_COMPARE_KEYWORDS = ("비교", "장점", "단점", "추천", "근거")
SPECULATION_KEYWORDS = ("추정", "아마", "가능성이", "예상")

GROUNDING_NOTICE = "※ 위 답변은 Vertex AI Search(Data Store) 검색 결과를 기반으로 작성되었습니다."
GITHUB_NOTICE = "※ 위 답변은 GitHub 조회 결과를 기준으로 정리되었습니다."

FULL_SHA_PATTERN = re.compile(r"\b[0-9a-f]{40}\b", re.IGNORECASE)
SHORT_SHA_PATTERN = re.compile(r"\b[0-9a-f]{7,39}\b", re.IGNORECASE)
URL_PATTERN = re.compile(r"https?://[^\s]+", re.IGNORECASE)

RAW_METADATA_HINTS = (
    '"sha"',
    "'sha'",
    '"html_url"',
    "'html_url'",
    '"node_id"',
    "'node_id'",
    '"url"',
    "'url'",
    '"commit"',
    "'commit'",
)

OBVIOUSLY_OUT_OF_SCOPE_KEYWORDS = (
    "날씨",
    "운세",
    "사주",
    "타로",
    "맛집",
    "주식 추천",
    "연예인",
)

SECRET_PATTERNS = (
    re.compile(r"gh[pousr]_[A-Za-z0-9_]+"),
    re.compile(r"AIza[0-9A-Za-z\-_]+"),
    re.compile(r"sk-[A-Za-z0-9]+"),
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
)


# =========================================================
# 공통 유틸
# =========================================================

def _state_get_from_obj(state_obj: Any, key: str, default: str = "") -> str:
    if state_obj is None:
        return default

    if hasattr(state_obj, "get"):
        value = state_obj.get(key, default)
    else:
        try:
            value = state_obj[key]
        except Exception:
            return default

    if value is None:
        return default
    return str(value).strip()


def _state_set_to_obj(state_obj: Any, key: str, value: object) -> None:
    if state_obj is None:
        return
    try:
        state_obj[key] = value
    except Exception:
        return


def _state_get(callback_context: CallbackContext, key: str, default: str = "") -> str:
    return _state_get_from_obj(getattr(callback_context, "state", None), key, default)


def _state_set(callback_context: CallbackContext, key: str, value: object) -> None:
    _state_set_to_obj(getattr(callback_context, "state", None), key, value)


def _tool_state_set(tool_context: ToolContext, key: str, value: object) -> None:
    _state_set_to_obj(getattr(tool_context, "state", None), key, value)


def _has_state_value(callback_context: CallbackContext, key: str) -> bool:
    return bool(_state_get(callback_context, key))


def _build_model_content(text: str) -> types.Content:
    return types.Content(role="model", parts=[types.Part(text=text)])


def _build_llm_response(text: str) -> LlmResponse:
    return LlmResponse(content=_build_model_content(text))


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _parse_prefixed_value(text: str, prefix: str) -> str:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.lower().startswith(prefix.lower()):
            return line[len(prefix):].strip()
    return ""


def _extract_user_text(callback_context: CallbackContext) -> str:
    content = getattr(callback_context, "user_content", None)
    if not content or not getattr(content, "parts", None):
        return ""

    texts = [part.text for part in content.parts if getattr(part, "text", None)]
    return " ".join(texts).strip().lower()


def _extract_text_from_llm_request(llm_request: LlmRequest) -> str:
    contents = getattr(llm_request, "contents", None) or []
    texts: list[str] = []

    for content in contents:
        parts = getattr(content, "parts", None) or []
        for part in parts:
            text = getattr(part, "text", None)
            if text:
                texts.append(text)

    return "\n".join(texts).strip().lower()


def _contains_secret(text: str) -> bool:
    if not text:
        return False
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def _looks_like_raw_metadata_dump(text: str) -> bool:
    if not text:
        return False

    hint_count = sum(1 for hint in RAW_METADATA_HINTS if hint in text)
    brace_like = text.count("{") + text.count("}")
    return hint_count >= 2 or brace_like >= 8


def _sanitize_github_text(
    text: str,
    *,
    allow_short_sha: bool = False,
    allow_url: bool = False,
) -> str:
    if not text:
        return ""

    sanitized = FULL_SHA_PATTERN.sub("[sha-hidden]", text)

    if not allow_short_sha:
        sanitized = SHORT_SHA_PATTERN.sub("[id-hidden]", sanitized)

    if not allow_url:
        sanitized = URL_PATTERN.sub("[link-hidden]", sanitized)

    return sanitized.strip()


def _user_explicitly_requests_github_link_or_sha(user_text: str) -> tuple[bool, bool]:
    if not user_text:
        return False, False

    allow_short_sha = any(
        keyword in user_text
        for keyword in ("sha", "short sha", "커밋 아이디", "커밋 sha", "짧은 sha")
    )
    allow_url = any(
        keyword in user_text
        for keyword in ("링크", "url", "주소", "커밋 링크")
    )
    return allow_short_sha, allow_url


# =========================================================
# 도메인 판별
# =========================================================

def _mentions_internal_doc_keyword(user_text: str) -> bool:
    return _contains_any(user_text, INTERNAL_DOC_KEYWORDS)


def _mentions_github_keyword(user_text: str) -> bool:
    return _contains_any(user_text, GITHUB_KEYWORDS)


def _has_internal_context(callback_context: CallbackContext) -> bool:
    if _state_get(callback_context, "internal_doc_mode") == "true":
        return True
    return any(_has_state_value(callback_context, key) for key in INTERNAL_CONTEXT_STATE_KEYS)


def _has_github_context(callback_context: CallbackContext) -> bool:
    if _state_get(callback_context, "github_mode") == "true":
        return True
    return any(_has_state_value(callback_context, key) for key in GITHUB_CONTEXT_STATE_KEYS)


def _looks_like_follow_up(user_text: str) -> bool:
    if not user_text:
        return False

    if _contains_any(user_text, FOLLOW_UP_REFERENTIAL_KEYWORDS):
        return True

    if len(user_text) <= 40 and _contains_any(user_text, FOLLOW_UP_INTENT_KEYWORDS):
        return True

    return False


def _needs_clarification(user_text: str) -> bool:
    """
    너무 짧고 도메인 힌트가 없는 입력은 라우팅 전 명확화 대상으로 본다.
    """
    if not user_text:
        return False

    if len(user_text) > 8:
        return False

    if _mentions_internal_doc_keyword(user_text) or _mentions_github_keyword(user_text):
        return False

    if _looks_like_follow_up(user_text):
        return False

    return True


def _is_obviously_out_of_scope(user_text: str) -> bool:
    if not user_text:
        return False

    if _mentions_internal_doc_keyword(user_text):
        return False

    if _mentions_github_keyword(user_text):
        return False

    return _contains_any(user_text, OBVIOUSLY_OUT_OF_SCOPE_KEYWORDS)


# =========================================================
# before_agent_callback
# =========================================================

def before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Supervisor 진입점 전용:
    - 내부 문서 / GitHub 관련 질문 허용
    - 기존 문맥 기반 후속 질문 허용
    - 명백히 무관한 질문만 차단
    """
    user_text = _extract_user_text(callback_context)

    if user_text:
        _state_set(callback_context, "user_query", user_text)
        _state_set(callback_context, "last_user_query", user_text)

    # 라우팅 전에 짧고 애매한 입력을 먼저 명확화한다.
    if _needs_clarification(user_text):
        return _build_model_content(
            "질문 의도를 조금 더 구체적으로 적어 주세요. <br>예: 문서명/프로젝트명/저장소명 + 궁금한 항목(원인, 비교, 설정 방법 등)."
        )

    if _mentions_internal_doc_keyword(user_text):
        _state_set(callback_context, "internal_doc_mode", "true")
        _state_set(callback_context, "github_mode", "false")
        _state_set(callback_context, "last_domain", "internal_doc")
        return None

    if _mentions_github_keyword(user_text):
        _state_set(callback_context, "github_mode", "true")
        _state_set(callback_context, "internal_doc_mode", "false")
        _state_set(callback_context, "last_domain", "github")
        return None

    if _has_internal_context(callback_context) and _looks_like_follow_up(user_text):
        _state_set(callback_context, "internal_doc_mode", "true")
        _state_set(callback_context, "last_domain", "internal_doc_follow_up")
        return None

    if _has_github_context(callback_context) and _looks_like_follow_up(user_text):
        _state_set(callback_context, "github_mode", "true")
        _state_set(callback_context, "last_domain", "github_follow_up")
        return None

    if _is_obviously_out_of_scope(user_text):
        return _build_model_content(
            "이 에이전트는 사내 문서, 사내 프로젝트, 내부 기술 자료, GitHub 저장소 관련 질문만 처리합니다. "
            "문서명, 프로젝트명, 저장소명, 브랜치명, 파일명 같은 업무 문맥을 포함해 다시 질문해 주세요."
        )

    return None


# =========================================================
# before_model_callback
# =========================================================

def before_model_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> Optional[LlmResponse]:
    """
    모델 호출 직전 검사:
    - state / request 내 민감정보 차단
    - 너무 짧고 애매한 후속 질문은 명확화 유도
    """
    request_text = _extract_text_from_llm_request(llm_request)
    user_text = _extract_user_text(callback_context)

    for key in (
        "rag_result",
        "summary",
        "parallel_rag_result",
        "parallel_web_result",
        "parallel_merged_result",
        "parallel_answer",
        "github_search_result",
        "github_answer",
        "answer",
    ):
        value = _state_get(callback_context, key)
        if value and _contains_secret(value):
            return _build_llm_response(
                "민감정보 또는 자격증명으로 보일 수 있는 내용이 감지되어 응답을 중단합니다. "
                "시크릿, 토큰, 키, 자격증명은 제거한 뒤 다시 요청해 주세요."
            )

    if _contains_secret(request_text):
        return _build_llm_response(
            "요청 내용에 민감정보 또는 자격증명으로 보일 수 있는 문자열이 포함되어 있어 응답을 중단합니다."
        )

    if (_has_internal_context(callback_context) or _has_github_context(callback_context)) and user_text and len(user_text) <= 8:
        if not _looks_like_follow_up(user_text):
            return _build_llm_response(
                "직전 맥락을 이어가는 질문이라면 문서명, 프로젝트명, 저장소명, 또는 '방금 기준으로' 같은 표현을 함께 적어 주세요."
            )

    return None


# =========================================================
# after_tool_callback
# =========================================================

def after_tool_callback(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    tool_response: Any,
) -> Optional[dict[str, Any]]:
    """
    tool 실행 후 후처리.
    - 민감정보 응답 차단
    - GitHub raw metadata 응답 여부만 state에 기록
    """
    _ = args
    tool_name = getattr(tool, "name", "") or ""
    response_text = str(tool_response)

    if _contains_secret(response_text):
        return {
            "error": "민감정보 또는 자격증명으로 보일 수 있는 내용이 감지되어 도구 결과를 반환하지 않습니다."
        }

    if "github" in tool_name.lower():
        if _looks_like_raw_metadata_dump(response_text):
            _tool_state_set(tool_context, "github_result_raw_like", "true")
        else:
            _tool_state_set(tool_context, "github_result_raw_like", "false")

    return None


# =========================================================
# after_agent_callback validators
# =========================================================

def _validate_rag_response(callback_context: CallbackContext) -> types.Content | None:
    answer = _state_get(callback_context, "answer")
    rag_result = _state_get(callback_context, "rag_result")

    if not rag_result:
        return _build_model_content(
            "관련 사내 문서를 찾지 못했습니다. 문서명, 프로젝트명, 고객사명, 기간, 기술 키워드를 더 구체적으로 포함해 다시 질문해 주세요."
        )

    if not answer:
        return _build_model_content(
            "문서 검색 결과는 있었지만 최종 답변 생성에 실패했습니다. 질문 범위를 조금 더 구체적으로 지정해 주세요."
        )

    if _contains_secret(answer):
        return _build_model_content(
            "답변 내용에 민감정보로 보일 수 있는 문자열이 감지되어 반환하지 않습니다."
        )

    if any(keyword in answer for keyword in SPECULATION_KEYWORDS) and "근거" not in answer:
        answer = (
            f"{answer.rstrip()}\n\n"
            "※ 일부 표현이 추정형일 수 있으므로, 반드시 검색된 문서 근거와 함께 확인해 주세요."
        )

    if GROUNDING_NOTICE not in answer:
        answer = f"{answer.rstrip()}\n\n{GROUNDING_NOTICE}"

    _state_set(callback_context, "internal_doc_mode", "true")
    _state_set(callback_context, "github_mode", "false")
    _state_set(callback_context, "last_domain", "internal_doc")
    return _build_model_content(answer)


def _normalize_rag_rewrite_state(callback_context: CallbackContext) -> types.Content | None:
    rag_rewrite_raw = _state_get(callback_context, "rag_rewrite")
    if not rag_rewrite_raw:
        return None

    parsed_query = _parse_prefixed_value(rag_rewrite_raw, "query:")
    parsed_filter = _parse_prefixed_value(rag_rewrite_raw, "filter_expr:")

    normalized_query = parsed_query or rag_rewrite_raw.strip()
    _state_set(callback_context, "rag_rewrite", normalized_query)
    _state_set(callback_context, "rag_filter_expr", parsed_filter)
    return None


def _validate_summary_response(callback_context: CallbackContext) -> types.Content | None:
    summary = _state_get(callback_context, "summary")

    if not summary:
        return _build_model_content(
            "문서 요약 결과가 비어 있습니다. 요약 대상 문서나 검색 결과를 다시 확인해 주세요."
        )

    if _contains_secret(summary):
        return _build_model_content(
            "요약 내용에 민감정보로 보일 수 있는 문자열이 감지되어 반환하지 않습니다."
        )

    if not any(keyword in summary for keyword in SUMMARY_SECTION_KEYWORDS):
        summary = f"핵심 요약\n{summary.strip()}"

    _state_set(callback_context, "internal_doc_mode", "true")
    _state_set(callback_context, "github_mode", "false")
    _state_set(callback_context, "last_domain", "internal_doc")
    return _build_model_content(summary)


def _validate_tech_compare_response(callback_context: CallbackContext) -> types.Content | None:
    compare_result = _state_get(callback_context, "parallel_answer")

    if not compare_result:
        return _build_model_content(
            "기술 비교 결과가 비어 있습니다. 비교 대상 기술명, 문서 범위, 고객사 또는 프로젝트명을 더 구체적으로 지정해 주세요."
        )

    if _contains_secret(compare_result):
        return _build_model_content(
            "기술 비교 결과에 민감정보로 보일 수 있는 문자열이 감지되어 반환하지 않습니다."
        )

    if not any(keyword in compare_result for keyword in TECH_COMPARE_KEYWORDS):
        compare_result = (
            f"기술 비교 요약\n{compare_result.strip()}\n\n"
            "추천: 제공된 사내 문서 기준으로 비교 근거를 추가 확인해 주세요."
        )

    _state_set(callback_context, "internal_doc_mode", "true")
    _state_set(callback_context, "github_mode", "false")
    _state_set(callback_context, "last_domain", "internal_doc")
    return _build_model_content(compare_result)


def _validate_github_response(callback_context: CallbackContext) -> types.Content | None:
    github_answer = _state_get(callback_context, "github_answer")
    github_search_result = _state_get(callback_context, "github_search_result")
    github_raw_like = _state_get(callback_context, "github_result_raw_like", "")
    user_text = _state_get(callback_context, "last_user_query")

    if not github_search_result:
        return _build_model_content(
            "관련 GitHub 조회 결과를 찾지 못했습니다. 저장소명, 브랜치명, 파일명, 이슈/PR 번호 등을 더 구체적으로 적어 주세요."
        )

    if not github_answer:
        return _build_model_content(
            "GitHub 조회 결과는 있었지만 최종 요약 답변 생성에 실패했습니다. 요청 범위를 조금 더 구체적으로 지정해 주세요."
        )

    if _contains_secret(github_answer) or _contains_secret(github_search_result):
        return _build_model_content(
            "GitHub 응답 내용에 민감정보 또는 자격증명으로 보일 수 있는 문자열이 감지되어 반환하지 않습니다."
        )

    if github_raw_like == "true" or _looks_like_raw_metadata_dump(github_answer):
        return _build_model_content(
            "GitHub 원본 응답이 raw metadata 형태로 감지되어 그대로 반환하지 않습니다. "
            "커밋 메시지, 작성자, 날짜, 변경 요지 중심으로 다시 요약해 주세요."
        )

    allow_short_sha, allow_url = _user_explicitly_requests_github_link_or_sha(user_text)
    github_answer = _sanitize_github_text(
        github_answer,
        allow_short_sha=allow_short_sha,
        allow_url=allow_url,
    )

    normalized = (
        github_answer
        .replace("[sha-hidden]", "")
        .replace("[id-hidden]", "")
        .replace("[link-hidden]", "")
        .strip()
    )
    if len(normalized) < 8:
        return _build_model_content(
            "GitHub 결과는 확인되었지만 기본 정책상 상세 식별자는 제외했습니다. 필요하면 'short SHA만 보여줘' 또는 '커밋 링크 줘'처럼 명시적으로 요청해 주세요."
        )

    if GITHUB_NOTICE not in github_answer:
        github_answer = f"{github_answer.rstrip()}\n\n{GITHUB_NOTICE}"

    _state_set(callback_context, "github_mode", "true")
    _state_set(callback_context, "internal_doc_mode", "false")
    _state_set(callback_context, "last_domain", "github")
    return _build_model_content(github_answer)


# =========================================================
# after_agent_callback
# =========================================================

def after_agent_callback(callback_context: CallbackContext) -> types.Content | None:
    agent_name = getattr(callback_context, "agent_name", "")

    if agent_name == "RagRewriteAgent":
        return _normalize_rag_rewrite_state(callback_context)

    if agent_name == "RagAnswerAgent":
        return _validate_rag_response(callback_context)

    if agent_name == "DocuGenerationAgent":
        return _validate_summary_response(callback_context)

    if agent_name == "ParallelAnswerAgent":
        return _validate_tech_compare_response(callback_context)

    if agent_name == "GitHubAnswerAgent":
        return _validate_github_response(callback_context)

    return None
