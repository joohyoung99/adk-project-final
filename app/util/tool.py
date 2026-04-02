from __future__ import annotations

import re
from typing import Any
from google import genai
from google.genai import types
from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as discoveryengine

from app.config.settings import settings

import asyncio
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext










def search_vertex_rag(query: str) -> str:
    """Vertex RAG corpus를 조회해 질의 결과를 텍스트로 반환한다."""

    project = settings.google_cloud_project
    location = settings.vertex_rag_location
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


def _sanitize_datastore_filter(filter_expr: str) -> str:
    """Discovery Engine에서 지원하지 않는 tags 조건을 제거한다."""

    if not filter_expr.strip():
        return ""

    clauses = [clause.strip() for clause in re.split(r"\s+AND\s+", filter_expr) if clause.strip()]
    sanitized = [clause for clause in clauses if not clause.lower().startswith("tags:")]
    return " AND ".join(sanitized)




def search_datastore(
    query: str,
    filter_expr: str = "",
    page_size: int = 5,
    return_summary: bool = True,
) -> dict[str, Any]:
    """Vertex AI Search(Data Store) 문서 검색"""

    if not query.strip():
        return {"error": "검색어가 비어 있습니다."}

    project_id = settings.google_cloud_project
    location = settings.discovery_engine_location
    engine_id = settings.discovery_engine_engine_id

    if not project_id or not location or not engine_id:
        return {"error": "Discovery Engine 환경 변수가 설정되지 않았습니다."}

    sanitized_filter_expr = _sanitize_datastore_filter(filter_expr)

    client_options = (
        ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
        if location != "global"
        else None
    )
    client = discoveryengine.SearchServiceClient(client_options=client_options)

    serving_config = (
        f"projects/{project_id}/locations/{location}/collections/default_collection/"
        f"engines/{engine_id}/servingConfigs/default_config"
    )

    content_search_spec = discoveryengine.SearchRequest.ContentSearchSpec(
        snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
            return_snippet=True
        ),
        summary_spec=(
            discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
                summary_result_count=min(page_size, 5),
                include_citations=True,
                ignore_adversarial_query=True,
                ignore_non_summary_seeking_query=True,
                model_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec.ModelSpec(
                    version="stable"
                ),
            )
            if return_summary
            else None
        ),
    )

    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=query,
        filter=sanitized_filter_expr,
        page_size=page_size,
        content_search_spec=content_search_spec,
        query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
            condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO
        ),
        spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
            mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO
        ),
    )

    try:
        pager = client.search(request=request)
    except Exception as e:
        return {"error": f"Discovery Engine 검색 실패: {e}"}

    raw_response = getattr(pager, "_response", None)
    summary_text = ""
    if raw_response and getattr(raw_response, "summary", None):
        summary_text = getattr(raw_response.summary, "summary_text", "") or ""

    results: list[dict[str, Any]] = []

    for item in pager:
        document = getattr(item, "document", None)
        if not document:
            continue

        struct_data = {}
        if getattr(document, "struct_data", None):
            try:
                struct_data = dict(document.struct_data)
            except Exception:
                struct_data = {}

        snippets: list[str] = []
        derived_struct_data = getattr(document, "derived_struct_data", None)
        snippet_items = (
            derived_struct_data.get("snippets", [])
            if isinstance(derived_struct_data, dict)
            else getattr(derived_struct_data, "snippets", None) or []
        )

        for snip in snippet_items:
            snippet_text = snip.get("snippet", "") if isinstance(snip, dict) else getattr(snip, "snippet", "")
            if snippet_text:
                snippets.append(str(snippet_text).strip())

        results.append(
            {
                "id": getattr(document, "id", "") or "",
                "title": getattr(document, "title", "") or "",
                "uri": getattr(document, "uri", "") or "",
                "snippet": "\n".join(snippets),
                "doc_type": struct_data.get("doc_type", ""),
                "doc_title": struct_data.get("doc_title", ""),
                "doc_description": struct_data.get("doc_description", ""),
                "doc_category": struct_data.get("doc_category", ""),
                "struct_data": struct_data,
            }
        )

    return {
        "query": query,
        "filter": sanitized_filter_expr,
        "total_size": len(results),
        "summary": summary_text,
        "results": results,
    }

rag_search_tool = FunctionTool(search_datastore)
