from __future__ import annotations

from google import genai
from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools import FunctionTool
from google.genai import types

from app.config.settings import settings
from app.mcp.toolsets import filesystem_toolset

from app.prompt.instructions import (
    rag_rewrite_instruction,
    merge_instruction,
    rag_answer_instruction,
    save_to_file_instruction,
    summary_only_instruction,
    rag_search_instruction,
    docu_rewrite_instruction, #추가
    docu_generation_instruction #추가
)
from app.tool.callbacks import after_agent_callback



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
                                    vector_distance_threshold=0.6,
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


    return response.text or ""



def make_merge_agent() -> LlmAgent:
    """수집 결과 병합 전용 에이전트를 만든다."""
    return LlmAgent(
        name= "MergeAgent",
        model= settings.model,
        instruction= merge_instruction,
        output_key= "merged_result",
   
    )



def make_save_to_file_agent() -> LlmAgent:
    """filesystem MCP로 결과를 저장하는 에이전트를 만든다."""
    return LlmAgent(
        name= "SaveToFileAgent",
        model= settings.model,
        instruction= save_to_file_instruction,
        tools= [filesystem_toolset],
        output_key= "save_result",
  
    )


def make_summary_only_agent() -> LlmAgent:
    """최종 응답을 간단히 요약하는 에이전트를 만든다."""
    return LlmAgent(
        name= "SummaryOnlyAgent",
        model= settings.model,
        instruction= summary_only_instruction,
    
    )


def make_rag_search_agent() -> LlmAgent:
    """Vertex RAG 검색 툴을 사용하는 에이전트를 만든다."""
  
    return LlmAgent(
        name= "RAGSearchAgent",
        model= settings.model,
        instruction= rag_search_instruction,
        tools= [FunctionTool(search_vertex_rag)],
        output_key= "rag_result",
  
    )


def make_rag_rewrite_agent() -> LlmAgent:
    return LlmAgent(
        name= "RagRewriteAgent",
        model= settings.model,
        instruction= rag_rewrite_instruction,
        output_key= "rag_rewrite",
    )

def make_rag_answer_agent() -> LlmAgent:
    return LlmAgent(
        name= "RagAnswerAgent",
        model= settings.model,
        instruction= rag_answer_instruction,
        output_key= "answer",
        after_agent_callback= after_agent_callback,
    )

def make_docu_rewrite_agent() -> LlmAgent:
    """문서 요약용 쿼리 재작성 에이전트를 만든다."""
    return LlmAgent(
        name="DocuRewriteAgent",
        model=settings.model,
        instruction=docu_rewrite_instruction,
        output_key="docu_rewrite", # 다음 에이전트에게 넘겨줄 메모지 이름표
    )

def make_docu_generation_agent() -> LlmAgent:
    """문서 요약 생성 에이전트를 만든다."""
    return LlmAgent(
        name="DocuGenerationAgent",
        model=settings.model,
        instruction=docu_generation_instruction,
        tools=[filesystem_toolset],
        output_key="summary",       # 🚨 핵심: callbacks.py의 요약 검증을 통과하기 위한 키워드
        after_agent_callback=after_agent_callback, 
    )