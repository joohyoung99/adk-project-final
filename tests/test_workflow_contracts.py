from app.tool.callbacks import after_agent_callback
from google.genai import types


class FakeCallbackContext:
    def __init__(self, agent_name: str, **state_values):
        self.agent_name = agent_name
        self.state = dict(state_values)
        self.user_content = None


def make_context(agent_name: str, **state_values) -> FakeCallbackContext:
    return FakeCallbackContext(agent_name, **state_values)


def extract_text(content: types.Content) -> str:
    assert content is not None
    return "".join(part.text for part in content.parts if getattr(part, "text", None))


def test_rag_answer_appends_grounding_notice() -> None:
    context = make_context(
        "RagAnswerAgent",
        rag_result="검색 결과 있음",
        answer="문서 기준 답변",
    )

    result = after_agent_callback(context)
    text = extract_text(result)

    assert "문서 기준 답변" in text
    assert "Vertex AI Search(Data Store) 검색 결과를 기반으로 작성되었습니다." in text


def test_docu_summary_adds_summary_heading_when_structure_is_missing() -> None:
    context = make_context(
        "DocuGenerationAgent",
        summary="간단 정리 결과",
    )

    result = after_agent_callback(context)
    text = extract_text(result)

    assert text.startswith("핵심 요약")
    assert "간단 정리 결과" in text


def test_parallel_answer_adds_compare_summary_and_recommendation_when_keywords_missing() -> None:
    context = make_context(
        "ParallelAnswerAgent",
        parallel_answer="내부 결과와 외부 결과를 정리한 초안",
    )

    result = after_agent_callback(context)
    text = extract_text(result)

    assert text.startswith("기술 비교 요약")
    assert "추천:" in text


def test_github_answer_masks_identifiers_and_adds_notice() -> None:
    context = make_context(
        "GitHubAnswerAgent",
        last_user_query="최근 커밋 요약해줘",
        github_search_result="커밋 조회 결과 있음",
        github_answer=(
            "commit 1234567890abcdef1234567890abcdef12345678 "
            "short abcdef1 "
            "https://github.com/example/repo/pull/1"
        ),
    )

    result = after_agent_callback(context)
    text = extract_text(result)

    assert "1234567890abcdef1234567890abcdef12345678" not in text
    assert "abcdef1" not in text
    assert "https://github.com/example/repo/pull/1" not in text
    assert "GitHub 조회 결과를 기준으로 정리되었습니다." in text
