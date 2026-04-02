from fastapi.testclient import TestClient

from app.api import main as api_main


class FakeExecutor:
    async def execute(self, query: str, session_id: str | None = None) -> dict:
        return {
            "answer": query,
            "session_id": session_id or "health-session",
        }


def test_healthz_returns_ok(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "ADKAgentExecutor", FakeExecutor)
    client = TestClient(api_main.create_app())

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
