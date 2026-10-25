import asyncio
import json
import httpx
import pytest

from wtr.agent import Agent
from wtr.game import Tournament
from wtr.models import TournamentConfig


def obs():
    return Tournament("private", TournamentConfig().model_dump()).observation()


def test_openrouter_receives_only_private_observation_and_validates_action(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only")
    observation = obs()

    def handler(request):
        payload = json.loads(request.content)
        context = json.loads(payload["messages"][1]["content"])
        assert context["observation"] == observation
        assert all("cards" not in p for p in context["observation"]["players"])
        return httpx.Response(
            200,
            json={
                "id": "test-request",
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "action": "fold",
                                    "summary": "Test response.",
                                    "uncertainty": "Limited evidence.",
                                    "evidence_ids": [],
                                }
                            )
                        }
                    }
                ],
                "usage": {"prompt_tokens": 10},
            },
        )

    decision = asyncio.run(
        Agent(
            "openrouter", "test/model", transport=httpx.MockTransport(handler)
        ).decide(observation)
    )
    assert decision["source"] == "openrouter"
    assert decision["action"] == "fold"
    assert decision["usage"]["prompt_tokens"] == 10


@pytest.mark.parametrize(
    "response",
    [
        {
            "action": "raise:999999",
            "summary": "Bad",
            "uncertainty": "Unknown",
            "evidence_ids": [],
        },
        {
            "action": "fold",
            "summary": "Bad",
            "uncertainty": "Unknown",
            "evidence_ids": ["invented"],
        },
    ],
)
def test_invalid_model_response_uses_legal_fallback(monkeypatch, response):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only")
    handler = lambda r: httpx.Response(
        200, json={"choices": [{"message": {"content": json.dumps(response)}}]}
    )
    observation = obs()
    result = asyncio.run(
        Agent(
            "openrouter", "test/model", transport=httpx.MockTransport(handler)
        ).decide(observation)
    )
    assert result["source"] == "heuristic"
    assert result["fallback"]
    assert result["action"] in [a["key"] for a in observation["legal"]]


def test_deadline_falls_back_and_does_not_retry(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only")
    monkeypatch.setenv("AGENT_DEADLINE_SECONDS", "0.01")

    async def handler(r):
        await asyncio.sleep(1)
        raise AssertionError("Should have been cancelled")

    a = Agent("openrouter", "test/model", transport=httpx.MockTransport(handler))
    result = asyncio.run(a.decide(obs()))
    assert result["fallback"] == "Model deadline exceeded"
    assert a.calls == 1


def test_call_budget_never_contacts_provider(monkeypatch):
    monkeypatch.setenv("AGENT_MAX_CALLS", "0")

    def handler(r):
        raise AssertionError("Budget must prevent request")

    result = asyncio.run(
        Agent(
            "openrouter", "test/model", transport=httpx.MockTransport(handler)
        ).decide(obs())
    )
    assert result["fallback"] == "Model call budget reached"
