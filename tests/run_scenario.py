"""
시나리오 테스트 실행 스크립트.

에이전트에 각 시나리오 질문을 보내고 실제 응답을
scenario_results.json 파일로 저장한다.

실행 방법:
    .venv/bin/python tests/run_scenario.py
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import vertexai
from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

from agent import root_agent
from app.config.settings import settings

FIXTURE_DIR = Path("tests/integration/fixture")
OUTPUT_FILE = Path("scenario_results.json")

# 시나리오 정의
SCENARIOS = [
    {
        "scenario_title": "긴 텍스트 요약",
        "fixture_file": "long_text.test.json",
    },
    {
        "scenario_title": "주제 외 질문 차단",
        "fixture_file": "off_topic.test.json",
    },
]


async def ask_agent(runner: Runner, session_id: str, query: str) -> str:
    """에이전트에 질문을 보내고 최종 응답 텍스트를 반환한다."""
    content = types.Content(
        role="user",
        parts=[types.Part(text=query)],
    )

    final_text = "(응답 없음)"
    async for event in runner.run_async(
        user_id=settings.user_id,
        session_id=session_id,
        new_message=content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            texts = [
                part.text
                for part in event.content.parts
                if getattr(part, "text", None)
            ]
            final_text = "".join(texts).strip()

    return final_text


async def run() -> None:
    vertexai.init(
        project=settings.google_cloud_project,
        location=settings.google_cloud_location,
    )

    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()

    runner = Runner(
        app_name=settings.google_agent_engine_name,
        agent=root_agent,
        session_service=session_service,
        artifact_service=artifact_service,
    )

    results = []

    for scenario in SCENARIOS:
        print(f"\n[실행 중] {scenario['scenario_title']}")

        fixture_path = FIXTURE_DIR / scenario["fixture_file"]
        with open(fixture_path, "r", encoding="utf-8") as f:
            test_data = json.load(f)

        query = test_data[0]["query"]

        session = await session_service.create_session(
            app_name=settings.google_agent_engine_name,
            user_id=settings.user_id,
        )

        response = await ask_agent(runner, session.id, query)

        print(f"[완료] {scenario['scenario_title']}")

        results.append({
            "scenario_title": scenario["scenario_title"],
            "turns": [
                {
                    "request": query,
                    "response": response,
                }
            ],
        })

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n결과 저장 완료 → {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(run())
