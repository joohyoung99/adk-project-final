from app.tool.callbacks import (
    _is_obviously_out_of_scope,
    _needs_clarification,
    _sanitize_github_text,
)


def test_needs_clarification_for_short_ambiguous_input() -> None:
    assert _needs_clarification("도와줘") is True


def test_needs_clarification_false_for_internal_doc_query() -> None:
    assert _needs_clarification("사내 문서") is False


def test_out_of_scope_for_non_work_query() -> None:
    assert _is_obviously_out_of_scope("오늘 날씨 알려줘") is True


def test_out_of_scope_false_for_github_query() -> None:
    assert _is_obviously_out_of_scope("github repo 구조 알려줘") is False


def test_sanitize_github_text_hides_sha_and_url_by_default() -> None:
    text = (
        "commit 1234567890abcdef1234567890abcdef12345678 "
        "short abcdef1 "
        "https://github.com/joohyoung99/adk-project-final"
    )

    sanitized = _sanitize_github_text(text)

    assert "[sha-hidden]" in sanitized
    assert "[id-hidden]" in sanitized
    assert "[link-hidden]" in sanitized


def test_sanitize_github_text_keeps_explicitly_allowed_values() -> None:
    text = "short abcdef1 https://github.com/joohyoung99/adk-project-final"

    sanitized = _sanitize_github_text(
        text,
        allow_short_sha=True,
        allow_url=True,
    )

    assert "abcdef1" in sanitized
    assert "https://github.com/joohyoung99/adk-project-final" in sanitized
