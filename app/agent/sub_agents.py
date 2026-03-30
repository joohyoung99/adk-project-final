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
    web_search_instruction,
    parallel_rewrite_instruction,
    parallel_answer_instruction,
)
from app.tool.callbacks import after_agent_callback
from app.util.tool import search_vertex_rag 


def make_web_search_agent() -> LlmAgent:
    """웹 검색 전용 에이전트를 만든다."""
    return LlmAgent(
        name= "WebSearchAgent",
        model= settings.model,
        instruction = web_search_instruction,
        tools= [web_search_tool],
        output_key= "web_search_result",
    )


def make_parallel_rewrite_agent() -> LlmAgent:
    """병렬 수집용 쿼리 재작성 에이전트를 만든다."""
    return LlmAgent(
        name= "ParallelRewriteAgent",
        model= settings.model,
        instruction= parallel_rewrite_instruction,
        output_key= "parallel_rewrite",
    )



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
        tools= [search_vertex_rag],
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

def make_parallel_answer_agent() -> LlmAgent:
    return LlmAgent(
        name= "ParallelAnswerAgent",
        model= settings.model,
        instruction= parallel_answer_instruction,  
        output_key= "parallel_answer",
        after_agent_callback= after_agent_callback,  
    )