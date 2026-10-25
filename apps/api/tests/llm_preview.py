"""Local integration preview: real API/workers, explicitly mocked provider calls.

Run from apps/api with a disposable DATABASE_URL and an allowed frontend origin:
    .venv/bin/python tests/llm_preview.py
Never imported by production. Models, messages and usage are synthetic QA data.
"""

import asyncio
import os

import httpx
import uvicorn

# Override ambient provider configuration before importing the application.
os.environ.update(
    OPENROUTER_API_KEY="integration-mock-only",
    OPENROUTER_MODEL="test/integration-mock",
    LANGSMITH_TRACING="false",
    LANGCHAIN_TRACING_V2="false",
)

from wtr import workers
from wtr.llmbench.runner import MockProvider
from wtr.main import app
from wtr.tableplay import TablePlay


class PreviewPlay(TablePlay):
    def __init__(self, *args, **kwargs):
        provider = MockProvider()

        async def delayed(request):
            await asyncio.sleep(0.25)
            return await provider(request)

        super().__init__(
            *args, **kwargs, transport=httpx.MockTransport(delayed), export_traces=False
        )


# Spawned workers also execute this module, preserving the mocked transport.
workers.TablePlay = PreviewPlay

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("PREVIEW_PORT", "8016")))
