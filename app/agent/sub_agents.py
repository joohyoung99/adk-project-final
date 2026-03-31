from __future__ import annotations

from google import genai
from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools import google_search
from google.genai import types

from app.config.settings import settings
from app.mcp.toolsets import filesystem_toolset , github_mcp_toolset

from app.prompt.instructions import (
    rag_rewrite_instruction,
    rag_search_instruction,
    rag_answer_instruction,

    parallel_rewrite_instruction,
    parallel_rag_search_instruction,
    parallel_web_search_instruction,
    parallel_merge_instruction,
    parallel_answer_instruction,
    
    docu_rewrite_instruction,
    docu_generation_instruction,
    
    github_rewrite_instruction,
    github_search_instruction,
    github_answer_instruction
       
)
from app.tool.callbacks import after_agent_callback , before_agent_callback ,   after_tool_callback , before_model_callback
from app.util.tool import search_vertex_rag 





#########################
# Parallel Agent Instructions
#########################

def make_parallel_rewrite_agent() -> LlmAgent:
    """병렬 수집용 쿼리 재작성 에이전트를 만든다."""
    return LlmAgent(
        name= "ParallelRewriteAgent",
        model= settings.model,
        instruction= parallel_rewrite_instruction,
        output_key= "parallel_rewrite",
        before_model_callback=before_model_callback,
    )


def make_parallel_web_search_agent() -> LlmAgent:
    """웹 검색 전용 에이전트를 만든다."""
    return LlmAgent(
        name= "ParallelWebSearchAgent",
        model= settings.model,
        instruction = parallel_web_search_instruction,
        tools= [google_search],
        output_key= "parallel_web_result",
        before_model_callback=before_model_callback,
        after_tool_callback= after_tool_callback,
    )


def make_parallel_rag_search_agent() -> LlmAgent:
    """Vertex RAG 검색 툴을 사용하는 에이전트를 만든다."""
  
    return LlmAgent(
        name= "ParallelRAGSearchAgent",
        model= settings.model,
        instruction= parallel_rag_search_instruction,
        tools= [search_vertex_rag],
        output_key= "parallel_rag_result",
        before_model_callback=before_model_callback,
        after_tool_callback= after_tool_callback,
    )

def make_parallel_merge_agent() -> LlmAgent:
    """수집 결과 병합 전용 에이전트를 만든다."""
    return LlmAgent(
        name= "ParallelMergeAgent",
        model= settings.model,
        instruction= parallel_merge_instruction,
        output_key= "parallel_merged_result",
        before_model_callback=before_model_callback,
    )


def make_parallel_answer_agent() -> LlmAgent:
    return LlmAgent(
        name= "ParallelAnswerAgent",
        model= settings.model,
        instruction= parallel_answer_instruction,  
        output_key= "parallel_answer",
        before_model_callback=before_model_callback,
        after_agent_callback= after_agent_callback,  
    )



def make_rag_search_agent() -> LlmAgent:
    """Vertex RAG 검색 툴을 사용하는 에이전트를 만든다."""
  
    return LlmAgent(
        name= "RAGSearchAgent",
        model= settings.model,
        instruction= rag_search_instruction,
        tools= [search_vertex_rag],
        output_key= "rag_result",
        before_model_callback=before_model_callback,
        after_tool_callback= after_tool_callback,
    )


def make_rag_rewrite_agent() -> LlmAgent:
    return LlmAgent(
        name= "RagRewriteAgent",
        model= settings.model,
        instruction= rag_rewrite_instruction,
        output_key= "rag_rewrite",
        before_model_callback=before_model_callback,
    )

def make_rag_answer_agent() -> LlmAgent:
    return LlmAgent(
        name= "RagAnswerAgent",
        model= settings.model,
        instruction= rag_answer_instruction,
        output_key= "answer",
        before_model_callback=before_model_callback,
        after_agent_callback= after_agent_callback,  
    )






def make_docu_rewrite_agent() -> LlmAgent:
    """문서 요약용 쿼리 재작성 에이전트를 만든다."""
    return LlmAgent(
        name="DocuRewriteAgent",
        model=settings.model,
        instruction=docu_rewrite_instruction,
        output_key="docu_rewrite", # 다음 에이전트에게 넘겨줄 메모지 이름표
        before_model_callback=before_model_callback,  
    )

def make_docu_generation_agent() -> LlmAgent:
    """문서 요약 생성 에이전트를 만든다."""
    return LlmAgent(
        name="DocuGenerationAgent",
        model=settings.model,
        instruction=docu_generation_instruction,
        tools=[filesystem_toolset],   ## 수정?
        output_key="summary",       # 🚨 핵심: callbacks.py의 요약 검증을 통과하기 위한 키워드
        before_model_callback=before_model_callback,
        after_tool_callback=after_tool_callback,
        after_agent_callback=after_agent_callback, 
    )


#############################################################################
############ GITHUB MCP 관련 에이전트 ############
#############################################################################

#TODO : GitHub 검색용 에이전트 프롬프트 정의할 것. (쿼리 재작성, 검색, 답변 생성)
# 사내 프로젝트 깃헙 코드나 워크트리를 보면서 프로젝트 관련 정보를 찾을 수 있게 함


def make_github_rewrite_agent() -> LlmAgent:
    """GitHub 검색용 쿼리 재작성 에이전트를 만든다."""
    return LlmAgent(
        name="GitHubRewriteAgent",
        model=settings.model,
        instruction=github_rewrite_instruction,
        output_key="github_rewrite",
        before_model_callback=before_model_callback,
    )


def make_github_search_agent() -> LlmAgent:
    """GitHub 검색 전용 에이전트를 만든다."""
    return LlmAgent(
        name= "GitHubSearchAgent",
        model= settings.model,
        instruction = github_search_instruction,
        tools= [github_mcp_toolset],  # GitHub 검색 도구 사용
        output_key= "github_search_result",
        before_model_callback=before_model_callback,
        after_tool_callback= after_tool_callback,
    )

def make_github_answer_agent() -> LlmAgent:
    """GitHub 검색 결과를 바탕으로 답변 생성 에이전트를 만든다."""
    return LlmAgent(
        name= "GitHubAnswerAgent",
        model= settings.model,
        instruction = github_answer_instruction, 
        output_key= "github_answer",
        before_model_callback=before_model_callback,
        after_agent_callback= after_agent_callback,  
    )
