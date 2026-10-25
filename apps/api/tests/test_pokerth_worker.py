"""Full production table loop, real native opponents, mocked external model only."""

import json
import multiprocessing as mp
import os
import time

import httpx
from fastapi.testclient import TestClient

from wtr.agent import Agent
from wtr.main import app
from wtr.models import TournamentConfig
from wtr.store import Store
from wtr.workers import table_worker
from test_api import wait_for


def mocked_provider(request):
    obs = json.loads(json.loads(request.content)["messages"][1]["content"])[
        "observation"
    ]
    serialized = json.dumps(obs)
    for forbidden in (
        "opponent_seed",
        "personality_seed",
        "profiles",
        "source_code",
        "pokerth",
    ):
        assert forbidden not in serialized
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
                                "summary": "Mock provider decision for native integration test.",
                                "uncertainty": "Test response, not strategic advice.",
                                "evidence_ids": [],
                            }
                        )
                    }
                }
            ]
        },
    )


class MockAgent(Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args, **kwargs, transport=httpx.MockTransport(mocked_provider)
        )


def provider_worker(*args):
    from wtr import workers

    os.environ.update(
        OPENROUTER_API_KEY="mock-only",
        LANGSMITH_TRACING="false",
        LANGCHAIN_TRACING_V2="false",
        AGENT_MAX_CALLS="1000",
    )
    workers.Agent = MockAgent
    workers.table_worker(*args)


def test_native_worker_pair_controls_completion_traces_and_replay(
    tmp_path, monkeypatch
):
    url = f"sqlite:///{tmp_path}/native.sqlite"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.delenv("CONTROL_TOKEN", raising=False)
    monkeypatch.setenv("WTR_PUBLIC", "false")
    ctx = mp.get_context("spawn")
    store = Store(url)
    store.initialize()
    ids = ["native-heuristic", "native-provider-mock"]
    processes, queues = [], []
    try:
        for index, table_id in enumerate(ids):
            config = TournamentConfig(
                seed=7,
                stack_bb=10,
                hands_per_level=2,
                pace=0.05,
                opponents="pokerth",
                opponent_seed=91,
                personality_seed=44,
                hero_seed=42,
                mode="openrouter" if index else "heuristic",
                model="test/mock" if index else "",
            ).model_dump()
            store.create(table_id, config)
            commands = ctx.Queue()
            process = ctx.Process(
                target=provider_worker if index else table_worker,
                args=(table_id, config, commands, url),
            )
            process.start()
            queues.append(commands)
            processes.append(process)
        assert len({p.pid for p in processes}) == 2

        def wait(table_id, predicate):
            deadline = time.monotonic() + 40
            while time.monotonic() < deadline:
                table = next(t for t in store.list() if t["id"] == table_id)
                assert table["status"] != "error", table.get("error")
                if predicate(table):
                    return table
                time.sleep(0.03)
            raise AssertionError(f"Worker did not reach state: {table['status']}")

        initial = [wait(i, lambda t: t.get("version", 0) > 0) for i in ids]
        queues[0].put({"action": "step"})
        stepped = wait(ids[0], lambda t: t["version"] >= initial[0]["version"] + 2)
        assert stepped["status"] == "paused"
        assert (
            next(t for t in store.list() if t["id"] == ids[1])["version"]
            == initial[1]["version"]
        )
        queues[0].put({"action": "resume"})
        wait(ids[0], lambda t: t["version"] > stepped["version"] + 2)
        queues[0].put({"action": "pause"})
        paused = wait(ids[0], lambda t: t["status"] == "paused")
        time.sleep(0.15)
        assert (
            next(t for t in store.list() if t["id"] == ids[0])["version"]
            == paused["version"]
        )
        for queue in queues:
            queue.put({"action": "resume"})
        roots = []
        for index, table_id in enumerate(ids):
            final = wait(table_id, lambda t: t["status"] == "finished")
            assert final["remaining"] == 1
            assert sum(p["stack"] for p in final["players"]) == 600
            assert sum(p["prize"] for p in final["players"]) == 100
            assert final["agent_decisions"] > 0
            frames = store.history(table_id, limit=200)
            assert len(frames) > 10 and all(f["id"] == table_id for f in frames)
            assert all(
                sum(p["stack"] for p in f["players"]) + f["pot"] == 600 for f in frames
            )
            assert any(
                sum(not p["eliminated"] for p in f["players"]) == 2 for f in frames
            )
            records = store.list_traces(table_id, limit=200)["items"]
            assert records and all(r["status"] == "completed" for r in records)
            roots.append({r["trace_id"] for r in records})
            details = [store.get_trace(table_id, r["trace_id"]) for r in records]
            text = json.dumps(details)
            assert "personality_seed" not in text and "opponent_seed" not in text
            assert ("model_call" in text) == bool(index)
            if index:
                assert final["decision"]["source"] == "openrouter"
                assert final["decision"]["fallback"] is None
        assert roots[0].isdisjoint(roots[1])
        for process in processes:
            process.join(3)
            assert process.exitcode == 0
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(3)
            process.close()
        for queue in queues:
            queue.close()
            queue.join_thread()
        store.engine.dispose()
    # Production API reads replay and traces after both owners have exited.
    with TestClient(app) as client:
        for table_id in ids:
            assert client.get(f"/api/tables/{table_id}/history").json()
            assert client.get(f"/api/tables/{table_id}/traces").json()["items"]


def test_native_api_setup_error_and_stop_cleanup(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/setup.sqlite")
    monkeypatch.delenv("CONTROL_TOKEN", raising=False)
    monkeypatch.setenv("WTR_PUBLIC", "false")
    with TestClient(app) as client:
        monkeypatch.setenv("POKERTH_BINARY", str(tmp_path / "absent"))
        response = client.post("/api/tables", json={"opponents": "pokerth"})
        assert response.status_code == 409 and "build_pokerth.py" in response.text
        assert client.get("/api/tables").json() == []
        monkeypatch.delenv("POKERTH_BINARY")
        response = client.post(
            "/api/tables", json={"opponents": "pokerth", "pace": 0.05}
        )
        assert response.status_code == 201
        table_id = response.json()["id"]
        wait_for(client, table_id, lambda t: t.get("version", 0) > 0)
        client.post(f"/api/tables/{table_id}/control", json={"action": "resume"})
        wait_for(client, table_id, lambda t: t["version"] > 3)
        client.post(f"/api/tables/{table_id}/control", json={"action": "stop"})
        wait_for(client, table_id, lambda t: t["status"] == "stopped")
    assert app.state.manager.workers == {}
