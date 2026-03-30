from __future__ import annotations

from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools import AgentTool

from app.agent.workflows import run_sequential_docu_summary_pipeline, run_parallel_tech_compare_pipeline, run_sequential_rag_pipeline, run_sequential_docu_summary_pipeline
from app.config.settings import settings
from app.prompt.instructions import supervisor_instruction
from app.tool.callbacks import before_agent_callback


supervisor_agent = LlmAgent(
    name="SupervisorAgent",
    model=settings.model,
    instruction="당신은 친절한 답변 생성기입니다.",
    # instruction=supervisor_instruction,
    # tools=[
    #     docu_summary_tool,
    #     tech_compare_tool,
    #     rag_tool
    # ],
    before_agent_callback=before_agent_callback
)

root_agent = supervisor_agent
