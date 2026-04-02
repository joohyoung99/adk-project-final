from fastapi.testclient import TestClient

from app.api import main as api_main


class FakeExecutor:
    async def execute(self, query: str, session_id: str | None = None) -> dict:
        return {
            "answer": f"echo:{query}",
            "session_id": session_id or "generated-session-id",
        }


def create_test_client(monkeypatch) -> TestClient:
    monkeypatch.setattr(api_main, "ADKAgentExecutor", FakeExecutor)
    app = api_main.create_app()
    app.state.executor = FakeExecutor()
    return TestClient(app)


def test_query_returns_422_when_query_missing(monkeypatch) -> None:
    client = create_test_client(monkeypatch)

    response = client.post("/v1/query", json={})

    assert response.status_code == 422


def test_query_returns_422_when_query_is_empty(monkeypatch) -> None:
    client = create_test_client(monkeypatch)

    response = client.post("/v1/query", json={"query": ""})

    assert response.status_code == 422


def test_query_returns_answer_and_session_id(monkeypatch) -> None:
    client = create_test_client(monkeypatch)

    response = client.post(
        "/v1/query",
        json={
            "query": "AgentBuilder 관련 문서 찾아줘",
            "session_id": "existing-session",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["answer"] == "echo:AgentBuilder 관련 문서 찾아줘"
    assert payload["data"]["session_id"] == "existing-session"
    assert payload["data"]["citations"] == []
    assert isinstance(payload["trace"]["request_id"], str)
    assert isinstance(payload["trace"]["latency_ms"], int)
