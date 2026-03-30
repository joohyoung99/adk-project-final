from __future__ import annotations

from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools import AgentTool

from app.agent.workflows import docu_summary_tool, tech_compare_tool, rag_tool
from app.config.settings import settings
from app.prompt.instructions import supervisor_instruction
from app.tool.callbacks import before_agent_callback


supervisor_agent = LlmAgent(
    name="SupervisorAgent",
    model=settings.model,
    instruction=supervisor_instruction,
    tools=[
        docu_summary_tool,
        tech_compare_tool,
        rag_tool
    ],
    before_agent_callback=before_agent_callback
)

root_agent = supervisor_agent
