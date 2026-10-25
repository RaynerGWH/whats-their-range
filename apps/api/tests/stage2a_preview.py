"""Stage 2A browser QA bootstrap: real native opponents, mock model only. Mock all model calls, including child processes.

Run from apps/api with DATABASE_URL pointing to a disposable SQLite file.
Never imported by the production API.
"""

import asyncio
import json
import os

import httpx
import uvicorn

os.environ.update(
    OPENROUTER_API_KEY="stage2a-mock-only",
    OPENROUTER_MODEL="stage2a/mock",
    LANGSMITH_TRACING="false",
    LANGCHAIN_TRACING_V2="false",
)
from wtr.agent import Agent
from wtr import workers


async def mock_provider(request):
    await asyncio.sleep(0.3)
    obs = json.loads(json.loads(request.content)["messages"][1]["content"])[
        "observation"
    ]
    if obs["hand"] % 2 == 0:
        return httpx.Response(503, text="mock upstream error must not enter traces")
    action = next(a["key"] for a in obs["legal"] if a["kind"] == "call")
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "action": action,
                                "summary": "Mock provider response for local interface verification.",
                                "uncertainty": "Not a strategic recommendation.",
                                "evidence_ids": [],
                            }
                        )
                    }
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        },
    )


class MockAgent(Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, transport=httpx.MockTransport(mock_provider))


workers.Agent = MockAgent

if __name__ == "__main__":
    uvicorn.run("wtr.main:app", host="127.0.0.1", port=8012)
