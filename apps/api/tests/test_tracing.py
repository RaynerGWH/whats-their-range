import asyncio
import json
import threading
import time
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker
from wtr import agent as agent_module
from wtr.agent import Agent
from wtr.game import Tournament
from wtr.main import app
from wtr.models import TournamentConfig
from wtr.store import Store, events, sessions
from wtr.tracing import LangSmithExporter, Trace, bounded, usage_from_provider

SCHEMA = json.loads(
    (Path(__file__).resolve().parents[3] / "contracts/trace-v1.schema.json").read_text()
)
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


@pytest.fixture(autouse=True)
def no_external_services(monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("WTR_PUBLIC", "false")
    monkeypatch.delenv("CONTROL_TOKEN", raising=False)


def observation(table="trace-test"):
    return Tournament(table, TournamentConfig().model_dump()).observation()


def run_agent(obs=None, **kwargs):
    agent = Agent(**kwargs)
    decision = asyncio.run(agent.decide(obs or observation()))
    return agent, decision


def response(action="fold", **extra):
    return {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "action": action,
                            "summary": "Test",
                            "uncertainty": "Test",
                            "evidence_ids": [],
                            **extra,
                        }
                    )
                }
            }
        ],
        "usage": {"prompt_tokens": 12, "completion_tokens": 3, "cost": 0.002},
    }


def test_real_spans_schema_parents_overlap_and_inflight(monkeypatch):
    barrier = threading.Barrier(2)

    def slow(fn):
        def wrapped(state):
            barrier.wait(timeout=3)
            time.sleep(0.03)
            return fn(state)

        return wrapped

    monkeypatch.setattr(agent_module, "assess", slow(agent_module.assess))
    monkeypatch.setattr(agent_module, "recall", slow(agent_module.recall))
    seen = []
    agent, result = run_agent(trace_sink=seen.append)
    record = agent.last_trace
    for item in seen:
        VALIDATOR.validate(item)
    assert any(
        s["status"] == "running" and s["duration_ms"] is None
        for r in seen
        for s in r["spans"]
    )
    assert result["trace_id"] == record["trace_id"]
    spans = {s["name"]: s for s in record["spans"]}
    assert set(spans) == {
        "decision",
        "assess_hand",
        "retrieve_evidence",
        "choose_action",
        "heuristic_selection",
    }
    root = spans["decision"]
    assert root["span_id"] == record["trace_id"] and root["parent_span_id"] is None
    assert (
        spans["heuristic_selection"]["parent_span_id"]
        == spans["choose_action"]["span_id"]
    )
    for name in ("assess_hand", "retrieve_evidence", "choose_action"):
        assert spans[name]["parent_span_id"] == root["span_id"]
    a, b = spans["assess_hand"], spans["retrieve_evidence"]
    assert max(a["start_offset_ms"], b["start_offset_ms"]) < min(
        a["start_offset_ms"] + a["duration_ms"], b["start_offset_ms"] + b["duration_ms"]
    )
    assert root["duration_ms"] >= 30
    assert root["duration_ms"] == record["duration_ms"]
    assert root["duration_ms"] < sum(s["duration_ms"] for s in record["spans"][1:])
    ids = [s["span_id"] for s in record["spans"]]
    assert len(set(ids)) == len(ids)
    for i in ids:
        UUID(i)


def test_model_messages_usage_and_private_filtering(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "secret-provider-key")
    obs = observation()
    obs["deck"] = ["hidden-deck"]
    obs["simulator"] = "hidden-simulator"
    obs["players"][1].update(cards=["hidden-cards"], profile="hidden-profile")
    obs["opponents"][0]["archetype"] = "hidden-archetype"
    sent = []

    def handler(request):
        sent.append(json.loads(request.content))
        data = response(headers="private-header", reasoning="private-reasoning")
        data["usage"]["secret"] = "secret-extra"
        return httpx.Response(200, json=data)

    agent, decision = run_agent(
        obs,
        mode="openrouter",
        model="test/model",
        transport=httpx.MockTransport(handler),
    )
    record = agent.last_trace
    VALIDATOR.validate(record)
    llm = next(s for s in record["spans"] if s["kind"] == "llm")
    assert llm["inputs"]["messages"] == sent[0]["messages"]
    assert llm["usage"] == {"input_tokens": 12, "output_tokens": 3, "cost_usd": 0.002}
    assert decision["source"] == "openrouter"
    all_data = json.dumps([record, sent, decision])
    for secret in (
        "hidden-deck",
        "hidden-simulator",
        "hidden-cards",
        "hidden-profile",
        "hidden-archetype",
        "secret-provider-key",
        "private-reasoning",
        "private-header",
        "secret-extra",
    ):
        assert secret not in all_data
    assert llm["outputs"]["action"] == "fold"
    assert usage_from_provider(
        {"prompt_tokens": True, "completion_tokens": -1, "cost": float("nan")}
    ) == {"input_tokens": None, "output_tokens": None, "cost_usd": None}


@pytest.mark.parametrize("failure", ["timeout", "http", "illegal", "malformed"])
def test_failure_spans_and_legal_fallback(monkeypatch, failure):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_DEADLINE_SECONDS", "0.02")

    async def handler(request):
        if failure == "timeout":
            await asyncio.sleep(1)
        if failure == "http":
            return httpx.Response(500, text="secret-provider-body")
        return httpx.Response(
            200, json=[] if failure == "malformed" else response("raise:999999")
        )

    agent, result = run_agent(
        mode="openrouter", model="test/model", transport=httpx.MockTransport(handler)
    )
    VALIDATOR.validate(agent.last_trace)
    spans = {s["name"]: s for s in agent.last_trace["spans"]}
    failed = "validate_response" if failure == "illegal" else "model_call"
    assert spans[failed]["status"] == "error"
    assert spans["fallback"]["status"] == "completed"
    assert agent.last_trace["status"] == "completed"
    assert result["action"] in [a["key"] for a in observation()["legal"]]
    assert "secret-provider-body" not in json.dumps(agent.last_trace)
    assert agent.calls == 1


def test_no_key_and_budget_have_no_fabricated_model_spans(monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    agent, result = run_agent(mode="openrouter", model="test/model")
    assert agent.exporter is None
    assert result["fallback"] == "OpenRouter key not configured"
    assert "model_call" not in [s["name"] for s in agent.last_trace["spans"]]
    monkeypatch.setenv("AGENT_MAX_CALLS", "0")
    agent, result = run_agent(mode="openrouter", model="test/model")
    assert result["fallback"] == "Model call budget reached"
    assert agent.calls == 0


def test_persistence_failure_does_not_change_action():
    def broken(record):
        raise RuntimeError("private-db-error")

    agent, result = run_agent(trace_sink=broken)
    assert result["action"] in [a["key"] for a in observation()["legal"]]
    assert agent.last_trace["metadata"]["persistence_failed"] is True
    assert "private-db-error" not in json.dumps(agent.last_trace)


def test_authenticated_pagination_cross_table_and_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/traces.sqlite")
    monkeypatch.setenv("CONTROL_TOKEN", "control-test")
    headers = {"Authorization": "Bearer control-test"}
    saved = []
    with TestClient(app) as client:
        for table in ("one", "two"):
            app.state.store.create(table, {})
        for hand in (1, 1, 2):
            obs = observation("one")
            obs["hand"] = hand
            agent, _ = run_agent(obs, trace_sink=app.state.store.save_trace)
            saved.append(agent.last_trace)
        url = "/api/tables/one/traces"
        assert client.get(url).status_code == 401
        assert client.get(url + "/" + saved[0]["trace_id"]).status_code == 401
        page = client.get(url, params={"limit": 2}, headers=headers).json()
        assert [r["trace_id"] for r in page["items"]] == [
            saved[2]["trace_id"],
            saved[1]["trace_id"],
        ]
        page2 = client.get(
            url, params={"limit": 2, "cursor": page["next_cursor"]}, headers=headers
        ).json()
        assert [r["trace_id"] for r in page2["items"]] == [saved[0]["trace_id"]]
        assert page2["next_cursor"] is None
        assert (
            len(client.get(url, params={"hand": 1}, headers=headers).json()["items"])
            == 2
        )
        assert (
            client.get(url, params={"limit": 201}, headers=headers).status_code == 422
        )
        assert (
            client.get(url, params={"cursor": "bad"}, headers=headers).status_code
            == 400
        )
        assert (
            client.get(
                "/api/tables/two/traces",
                params={"cursor": page["next_cursor"]},
                headers=headers,
            ).status_code
            == 400
        )
        assert (
            client.get("/api/tables/unknown/traces", headers=headers).status_code == 404
        )
        assert (
            client.get(
                "/api/tables/two/traces/" + saved[0]["trace_id"], headers=headers
            ).status_code
            == 404
        )
        assert (
            client.get(url + "/" + saved[0]["trace_id"], headers=headers).json()
            == saved[0]
        )
    with TestClient(app) as client:
        assert len(client.get(url, headers=headers).json()["items"]) == 3


def test_additive_initialization_retention_and_interrupted_trace(tmp_path, monkeypatch):
    store = Store(f"sqlite:///{tmp_path}/old.sqlite")
    sessions.create(store.engine)
    events.create(store.engine)
    store.create("old", {})
    store.initialize()
    monkeypatch.setenv("TRACE_MAX_PER_TABLE", "2")
    first = None
    for _ in range(3):
        agent, _ = run_agent(observation("old"), trace_sink=store.save_trace)
        first = first or agent.last_trace["trace_id"]
    assert store.get_trace("old", first) is None
    assert len(store.list_traces("old")["items"]) == 2
    trace = Trace(observation("old"))
    with trace.span("decision", root=True):
        store.save_trace(deepcopy(trace.record))
    store.engine.dispose()
    store = Store(f"sqlite:///{tmp_path}/old.sqlite")
    store.initialize()
    record = store.get_trace("old", trace.record["trace_id"])
    VALIDATOR.validate(record)
    assert record["status"] == "cancelled"
    assert record["duration_ms"] is None
    assert record["spans"][0]["status"] == "cancelled"
    store.engine.dispose()


def test_export_uses_real_sdk_run_tree_ids_messages_usage_and_url():
    agent, _ = run_agent()
    client = Mock()
    client._get_langsmith_api_sync.return_value.runs.get_url.return_value.url = (
        "https://smith.langchain.com/test-run"
    )
    saved = []
    exporter = LangSmithExporter(sink=saved.append, client_factory=lambda: client)
    exporter.submit(agent.last_trace)
    exporter.queue.join()
    exporter.close()
    assert saved[0]["langsmith_url"] == "https://smith.langchain.com/test-run"
    calls = [c.kwargs for c in client.create_run.call_args_list]
    assert len(calls) == len(agent.last_trace["spans"])
    assert all(str(c["trace_id"]) == agent.last_trace["trace_id"] for c in calls)
    for span, call in zip(agent.last_trace["spans"], calls):
        assert str(call["id"]) == span["span_id"]
        assert (
            str(call["parent_run_id"]) if call.get("parent_run_id") else None
        ) == span["parent_span_id"]


def test_export_queue_is_bounded_and_failure_does_not_block():
    started, release = threading.Event(), threading.Event()
    client = Mock()

    def blocked(**kwargs):
        started.set()
        release.wait(timeout=3)
        raise RuntimeError("private-telemetry-error")

    client.create_run.side_effect = blocked
    exporter = LangSmithExporter(client_factory=lambda: client, capacity=1)
    agent, _ = run_agent()
    exporter.submit(agent.last_trace)
    assert started.wait(2)
    start = time.perf_counter()
    for _ in range(50):
        exporter.submit(agent.last_trace)
    exporter.close(timeout=0.01)
    assert time.perf_counter() - start < 0.3
    assert exporter.queue.qsize() <= 1 and exporter.dropped >= 49
    release.set()
    exporter.thread.join(3)
    assert not exporter.thread.is_alive()


def test_payload_bounds_and_secret_redaction(monkeypatch):
    monkeypatch.setenv("CONTROL_TOKEN", "control-secret")
    assert bounded({"summary": "control-secret"})["summary"] == "[redacted]"
    assert bounded({"many": ["x" * 65536] * 200})["truncated"] is True


def test_inflight_worker_trace_keeps_state_version(tmp_path, monkeypatch):
    import queue

    from wtr import workers

    monkeypatch.setenv("OPENROUTER_API_KEY", "mock-key")
    entered, release = threading.Event(), threading.Event()

    async def handler(request):
        entered.set()
        while not release.is_set():
            await asyncio.sleep(0.01)
        return httpx.Response(200, json=response())

    original = workers.Agent
    monkeypatch.setattr(
        workers,
        "Agent",
        lambda *args, **kwargs: original(
            *args, **kwargs, transport=httpx.MockTransport(handler)
        ),
    )
    store = Store(f"sqlite:///{tmp_path}/inflight.sqlite")
    store.initialize()
    config = TournamentConfig(
        mode="openrouter", model="test/model", pace=0.05
    ).model_dump()
    store.create("inflight", config)
    commands = queue.Queue(maxsize=32)
    commands.close = lambda: None
    thread = threading.Thread(
        target=workers.table_worker,
        args=(
            "inflight",
            config,
            commands,
            store.engine.url.render_as_string(hide_password=False),
        ),
    )
    thread.start()
    try:
        commands.put({"action": "resume"})
        assert entered.wait(10)
        snapshot = store.list()[0]
        trace = store.get_trace("inflight", snapshot["active_trace_id"])
        VALIDATOR.validate(trace)
        assert trace["status"] == "running"
        assert trace["state_version"] == snapshot["version"]
        assert store.history("inflight")[-1]["version"] == snapshot["version"]
        commands.put({"action": "pause"})
        release.set()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            snapshot = store.list()[0]
            if snapshot["status"] == "paused" and snapshot["decision"]:
                break
            time.sleep(0.01)
        assert snapshot["active_trace_id"] is None
        assert snapshot["decision"]["trace_id"] == trace["trace_id"]
        assert store.get_trace("inflight", trace["trace_id"])["status"] == "completed"
    finally:
        release.set()
        commands.put({"action": "stop"})
        thread.join(5)
        store.engine.dispose()
    assert not thread.is_alive()


def test_export_model_format_with_installed_sdk(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "mock-key")
    agent, _ = run_agent(
        mode="openrouter",
        model="test/model",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=response())
        ),
    )
    client = Mock()
    client._get_langsmith_api_sync.return_value.runs.get_url.return_value.url = (
        "https://smith.langchain.com/test-run"
    )
    exporter = LangSmithExporter(client_factory=lambda: client)
    exporter.submit(agent.last_trace)
    exporter.queue.join()
    exporter.close()
    model = next(
        c.kwargs
        for c in client.create_run.call_args_list
        if c.kwargs["run_type"] == "llm"
    )
    assert model["inputs"]["messages"][0]["role"] == "system"
    assert model["outputs"]["usage_metadata"] == {
        "input_tokens": 12,
        "output_tokens": 3,
        "total_cost": 0.002,
    }
    assert (
        json.loads(model["outputs"]["choices"][0]["message"]["content"])["action"]
        == "fold"
    )
    assert model["extra"]["metadata"]["ls_provider"] == "openrouter"


def test_cancelled_decision_records_actual_cancelled_spans(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "mock-key")

    async def exercise():
        entered = asyncio.Event()

        async def handler(request):
            entered.set()
            await asyncio.sleep(10)

        agent = Agent(
            "openrouter", "test/model", transport=httpx.MockTransport(handler)
        )
        task = asyncio.create_task(agent.decide(observation()))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        return agent.last_trace

    record = asyncio.run(exercise())
    VALIDATOR.validate(record)
    assert record["status"] == "cancelled"
    spans = {s["name"]: s for s in record["spans"]}
    assert spans["model_call"]["status"] == "cancelled"
    assert "fallback" not in spans
