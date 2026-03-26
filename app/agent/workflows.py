from __future__ import annotations

from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.sequential_agent import SequentialAgent

from app.agent.sub_agents import (
    make_merge_agent,
    make_save_to_file_agent,
    make_summary_only_agent,
    make_ragengine_search_agent,
)

def parallel_collect_agent() -> ParallelAgent:
    """웹검색과 rag 검색 병렬 수집한다."""
    return ParallelAgent(
    name="ParallelCollectAgent",
    sub_agents=[],
    description="웹검색과 RAG 검색 병렬 실행 ",
)

def run_parallel_tech_compare_pipeline() -> SequentialAgent:
    """기술 비교용 병렬 수집 후 병합 파이프라인을 구성한다."""
    return SequentialAgent(
    name="run_parallel_tech_compare_pipeline",
    sub_agents=[
        # 쿼리 재작성 Agent 추가
        parallel_collect_agent(),
        make_merge_agent(),
        # 답변을 생성하는 Agent 추가
        # validation Agent 추가
    ],
    description="병렬 수집 후 머지해서 사용자에게 요약 응답한다.",
)


def run_sequential_docu_summary_pipeline() -> SequentialAgent:
    """문서 요약용 순차 파이프라인 골격을 구성한다."""
    return SequentialAgent(
    name="run_sequential_docu_summary_pipeline",
    sub_agents=[
       # 쿼리 재작성 Agent 추가
       # 답변 생성 Agent 추가 
       # validation Agent 추가
    ],
    description="사용자의 문서를 받고 요약 응답한다.",
)

def run_sequential_rag_pipeline() -> SequentialAgent:
    """Vertex RAG 검색 중심의 순차 파이프라인을 구성한다."""
    return SequentialAgent(
    name="run_sequential_rag_pipeline",
    sub_agents=[
        # 쿼리 재작성 Agent 추가
        make_ragengine_search_agent(),
        # 답변 생성 Agent 추가
        # validation Agent 추가
    ],
    description=(
        "RAG 엔진을 이용해 검색을 수행하고, 결과를 요약 응답한다."
    ),
)
