from __future__ import annotations

from google import genai
from google.genai import types

from app.config.settings import settings






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
