from __future__ import annotations

from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools import AgentTool

from app.agent.workflows import run_sequential_docu_summary_pipeline, run_parallel_tech_compare_pipeline, run_sequential_rag_pipeline
from app.config.settings import settings
from app.prompt.instructions import supervisor_instruction
from app.tool.callbacks import tool_callbacks


supervisor_agent = LlmAgent(
    name="SupervisorAgent",
    model=settings.model,
    instruction=supervisor_instruction,
    tools=[
        run_sequential_docu_summary_pipeline,
        run_parallel_tech_compare_pipeline,
        run_sequential_rag_pipeline

    ],
)

root_agent = supervisor_agent
