from __future__ import annotations

import json
import uuid
import vertexai

from google.adk.runners import Runner
from google.adk.sessions.vertex_ai_session_service import VertexAiSessionService
from google.genai import types

from agent import root_agent
from app.config.settings import settings



def ensure_model_api_key() -> None:
    """최소한 모델 설정값이 있는지 확인한다."""
    if not (settings.model):
        raise ValueError("GOOGLE_API_KEY 또는 GEMINI_API_KEY를 설정해야 합니다.")


def _compact(value: object, limit: int = 1000) -> str:
    """디버그 출력을 위해 긴 객체를 짧은 문자열로 압축한다."""
    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
    except TypeError:
        text = repr(value)
    if len(text) <= limit:
        return text
    return f"{text[:limit]}...<truncated>"


#TODO : 수정 
def print_event_debug(event: object) -> None:
    """ADK 이벤트 안의 함수 호출과 응답을 로그로 출력한다."""
    for function_call in event.get_function_calls():
        print(f"\n[FUNCTION CALL] {function_call.name}")
        print(_compact(function_call.args))

    for function_response in event.get_function_responses():
        print(f"\n[FUNCTION RESPONSE] {function_response.name}")
        print(_compact(function_response.response))


def print_banner() -> None:
    """CLI 시작 시 기본 안내 문구를 출력한다."""
    print("GCP 기반 사내 솔루션 문답 Agent")
    print(f"Filesystem allowed dirs: {', '.join(settings.filesystem_allowed_dirs)}")
    # TODO : GCP 환경 연결 상태도 보여주기
    print("종료: exit")


async def run_chat_cli() -> None:
    """Vertex AI 세션을 열고 사용자 입력을 반복 처리한다."""
    ensure_model_api_key()

    vertexai.init(
        project=settings.google_cloud_project,
        location= settings.google_cloud_location,
    )


    session_service = VertexAiSessionService(project=settings.google_cloud_project, 
                                             location=settings.google_cloud_location,
                                             ) 
    runner = Runner(
        app_name=settings.google_agent_engine_name,
        agent=root_agent,
        session_service=session_service,
    )
    session = await session_service.create_session(
        app_name=settings.google_agent_engine,
        user_id=settings.user_id,
    )

    print_banner()



    while True:
        user_input = input("\n> ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            break

        content = types.Content(
            role="user",
            parts=[types.Part(text=user_input)],
        )

        final_text = None
        async for event in runner.run_async(
            user_id=settings.user_id,
            session_id=session.id,
            new_message=content,
        ):
            

            print_event_debug(event)
            if event.is_final_response() and event.content and event.content.parts:
                texts = [part.text for part in event.content.parts if getattr(part, "text", None)]
                final_text = "".join(texts).strip()
        print("\n[Response]")
        print(final_text or "(응답 없음)")
