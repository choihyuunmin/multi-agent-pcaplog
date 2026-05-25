import asyncio
import time


def test_local_agent_does_not_wait_for_timeout(monkeypatch):
    monkeypatch.delenv("REDIS_HOST", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    from src.agents import ToolEnabledAgent

    async def run_once():
        start = time.perf_counter()
        result = await ToolEnabledAgent().ask("Analyze traffic for 192.168.10.50")
        elapsed = time.perf_counter() - start
        assert result["answer"]
        assert result["execution_log"]
        assert elapsed < 5

    asyncio.run(run_once())
