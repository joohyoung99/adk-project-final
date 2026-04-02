import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator

FIXTURE_DIR = "tests/integration/fixture"


@pytest.mark.asyncio
async def test_long_text_summary():
    """긴 텍스트를 직접 붙여넣었을 때 요약 파이프라인이 정상 동작하는지 확인."""
    await AgentEvaluator.evaluate(
        agent_module="app.agent",
        eval_dataset_file_path_or_dir=f"{FIXTURE_DIR}/long_text.test.json",
        num_runs=1,
    )


@pytest.mark.asyncio
async def test_off_topic_rejection():
    """주제 외 질문이 차단 메시지로 응답되는지 확인."""
    await AgentEvaluator.evaluate(
        agent_module="app.agent",
        eval_dataset_file_path_or_dir=f"{FIXTURE_DIR}/off_topic.test.json",
        num_runs=1,
    )
