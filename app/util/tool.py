from __future__ import annotations

from google import genai
from google.genai import types

from app.config.settings import settings

import asyncio
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types




def search_vertex_rag(query: str) -> str:
    """Vertex RAG corpus를 조회해 질의 결과를 텍스트로 반환한다."""

    project = settings.google_cloud_project
    location = settings.google_cloud_location
    rag_corpus = settings.vertex_rag_corpus
    
    if not project:
        return "Vertex RAG 검색 실패: GOOGLE_CLOUD_PROJECT 환경 변수가 필요합니다."
    if not rag_corpus:
        return "Vertex RAG 검색 실패: VERTEX_RAG_CORPUS 환경 변수가 필요합니다."

    client = genai.Client(
        vertexai=True,
        project=project,
        location=location,
    )

    response = client.models.generate_content(
        model=settings.model,
        contents=[
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=query)],
            ),
        ],
        config=types.GenerateContentConfig(
            temperature=1,
            tools=[
                types.Tool(
                    retrieval=types.Retrieval(
                        vertex_rag_store=types.VertexRagStore(
                            rag_resources=[
                                types.VertexRagStoreRagResource(
                                    rag_corpus=rag_corpus,
                                )
                            ],
                            rag_retrieval_config=types.RagRetrievalConfig(
                                filter=types.RagRetrievalConfigFilter(
                                    vector_distance_threshold=0.3,
                                ),
                                ranking=types.RagRetrievalConfigRanking(
                                    rank_service=types.RagRetrievalConfigRankingRankService(
                                        model_name="semantic-ranker-512",
                                    )
                                ),
                                top_k=5,
                            ),
                        )
                    )
                )
            ],
        ),
    )


    if not response.candidates:
        return "검색 결과가 없습니다."

    answer = response.text or "검색 결과가 없습니다."

    candidate = response.candidates[0]
    grounding_metadata = getattr(candidate, "grounding_metadata", None)

    titles : list[str] = []
    seen = set()

    if grounding_metadata and getattr(grounding_metadata, "grounding_chunks", None):
        for chunk in grounding_metadata.grounding_chunks:
            retrieved = getattr(chunk, "retrieved_context", None)
            if not retrieved:
                continue
            title = getattr(retrieved, "title", None)
            uri = getattr(retrieved, "uri", None)

            source_name = title or uri 
            if source_name and source_name not in seen:
                seen.add(source_name)
                titles.append(source_name)

    if titles:
        source_text = "\n".join(f"- {title}" for title in titles)
        return f"""{answer}

참고 문서:
{source_text}"""

    return answer


async def read_uploaded_artifact(tool_context: ToolContext):
    """사용자가 업로드한 아티팩트(파일)를 조회하여 반환한다."""
    try:
        available_files = await tool_context.list_artifacts()

        if not available_files:
            return ["업로드된 파일이 없습니다."]

        processed_results = []
        for filename in available_files:
            artifact = await tool_context.load_artifact(filename=filename)
            if not artifact or not artifact.inline_data:
                continue

            file_bytes = artifact.inline_data.data
            mime_type = artifact.inline_data.mime_type

            # PDF나 이미지는 멀티모달 Part로, 텍스트는 문자열로 처리
            if mime_type == "application/pdf" or mime_type.startswith("image/"):
                processed_results.append(types.Part.from_bytes(data=file_bytes, mime_type=mime_type))
            else:
                try:
                    text_content = file_bytes.decode('utf-8')
                    processed_results.append(f"[{filename} 내용]\n{text_content}")
                except UnicodeDecodeError:
                    processed_results.append(types.Part.from_bytes(data=file_bytes, mime_type=mime_type))
        return processed_results
    except Exception as e:
        return [f"파일 읽기 오류: {str(e)}"]

# 도구 객체 선언
artifact_read_tool = FunctionTool(func=read_uploaded_artifact)
