from typing import AsyncIterable, Optional

import vertexai
from google.adk import Runner
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService
from google.adk.sessions.vertex_ai_session_service import VertexAiSessionService
from google.genai import types

from app.agent.root import root_agent
from app.config.settings import settings


class ADKAgentExecutor:
    """ADK 에이전트 실행기"""

    def __init__(self):
        self._agent = root_agent
        self._app_name = self._agent.name
        session_service = InMemorySessionService()

        # Reasoning Engine이 설정된 경우에만 Vertex 세션 서비스를 사용한다.
        if settings.google_agent_engine_name:
            self._app_name = settings.google_agent_engine_name
            vertexai.init(
                project=settings.google_cloud_project,
                location=settings.reasoning_engine_location,
            )
            session_service = VertexAiSessionService(
                project=settings.google_cloud_project,
                location=settings.reasoning_engine_location,
            )

        self._runner = Runner(
            app_name=self._app_name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=session_service,
            memory_service=InMemoryMemoryService(),
        )

    @staticmethod
    def _extract_text(content: Optional[types.Content]) -> str:
        if not content or not content.parts:
            return ""
        texts = [part.text for part in content.parts if getattr(part, "text", None)]
        return "".join(texts).strip()

    async def execute(
        self,
        query: str,
        session_id: Optional[str] = None,
        user_id: str = "default_user"
    ) -> dict:
        """동기 실행: 최종 응답만 반환"""
        content = types.Content(role="user", parts=[types.Part(text=query)])

        # 세션 조회 또는 생성
        session = None
        if session_id:
            session = await self._runner.session_service.get_session(
                app_name=self._app_name,
                user_id=user_id,
                session_id=session_id,
            )
        if session is None:
            session = await self._runner.session_service.create_session(
                app_name=self._app_name,
                user_id=user_id,
            )

        # 에이전트 실행
        final_response = None
        async for event in self._runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=content,
        ):
            if event.is_final_response():
                text = self._extract_text(event.content)
                if text:
                    final_response = text

        return {
            "answer": final_response or "응답을 생성할 수 없습니다.",
            "session_id": session.id,
        }

    async def stream(
        self,
        query: str,
        session_id: Optional[str] = None,
        user_id: str = "default_user"
    ) -> AsyncIterable[dict]:
        """스트리밍 실행: 중간 업데이트 포함"""
        content = types.Content(role="user", parts=[types.Part(text=query)])

        # 세션 조회 또는 생성
        session = None
        if session_id:
            session = await self._runner.session_service.get_session(
                app_name=self._app_name,
                user_id=user_id,
                session_id=session_id,
            )
        if session is None:
            session = await self._runner.session_service.create_session(
                app_name=self._app_name,
                user_id=user_id,
            )

        async for event in self._runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=content,
        ):
            if event.is_final_response():
                response = self._extract_text(event.content)
                if response:
                    yield {"is_final": True, "content": response}
            else:
                yield {"is_final": False, "content": "처리 중..."}
