import time

from fastapi.testclient import TestClient
from wtr.main import app


def wait_for(client, table_id, predicate):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        app.state.manager.poll()
        table = next(t for t in client.get("/api/tables").json() if t["id"] == table_id)
        if predicate(table):
            return table
        time.sleep(0.05)
    raise AssertionError(f"Table did not reach expected state: {table}")


def test_two_tables_run_independently_and_replay_persists(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.sqlite")
    monkeypatch.delenv("CONTROL_TOKEN", raising=False)
    monkeypatch.setenv("WTR_PUBLIC", "false")
    with TestClient(app) as client:
        one = client.post("/api/tables", json={"seed": 1, "pace": 0.05}).json()["id"]
        two = client.post("/api/tables", json={"seed": 2, "pace": 0.05}).json()["id"]
        a = wait_for(client, one, lambda t: t.get("version", 0) > 0)
        b = wait_for(client, two, lambda t: t.get("version", 0) > 0)
        assert a["players"][0]["cards"] != b["players"][0]["cards"]
        assert client.post("/api/tables", json={}).status_code == 409
        client.post(f"/api/tables/{one}/control", json={"action": "resume"})
        a = wait_for(client, one, lambda t: t.get("version", 0) > 5)
        b2 = next(t for t in client.get("/api/tables").json() if t["id"] == two)
        assert b2["version"] == b["version"]
        client.post(f"/api/tables/{two}/control", json={"action": "step"})
        wait_for(client, two, lambda t: t["version"] > b["version"])
        client.post(f"/api/tables/{one}/control", json={"action": "stop"})
        wait_for(client, one, lambda t: t["status"] == "stopped")
        client.post(f"/api/tables/{two}/control", json={"action": "speed", "pace": 0.3})
        changed = wait_for(client, two, lambda t: t["config"]["pace"] == 0.3)
        assert changed["status"] == "paused"
        frames = client.get(f"/api/tables/{one}/history").json()
        assert len(frames) > 2
        assert all(f["id"] == one for f in frames)
        assert len({f["version"] for f in frames}) == len(frames)
    with TestClient(app) as client:
        assert len(client.get("/api/tables").json()) == 2
        assert client.get(f"/api/tables/{one}/history").json()


def test_access_control_and_missing_model_configuration(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/auth.sqlite")
    monkeypatch.setenv("CONTROL_TOKEN", "private-test")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with TestClient(app) as client:
        assert client.get("/api/tables").status_code == 401
        headers = {"Authorization": "Bearer private-test"}
        assert client.get("/api/tables", headers=headers).status_code == 200
        assert (
            client.post(
                "/api/tables",
                headers=headers,
                json={"mode": "openrouter", "model": "test/model"},
            ).status_code
            == 400
        )
        assert (
            client.post(
                "/api/tables", headers=headers, json={"stack_bb": -10}
            ).status_code
            == 422
        )


def test_trace_isolation_and_shutdown_without_websocket(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/isolation.sqlite")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("WTR_PUBLIC", "false")
    monkeypatch.delenv("CONTROL_TOKEN", raising=False)
    with TestClient(app) as client:
        ids = [
            client.post("/api/tables", json={"seed": seed, "pace": 0.05}).json()["id"]
            for seed in (7, 8)
        ]
        manager = app.state.manager
        assert len({manager.workers[i][0].pid for i in ids}) == 2
        for table_id in ids:
            client.post(f"/api/tables/{table_id}/control", json={"action": "resume"})
        for table_id in ids:
            wait_for(client, table_id, lambda t: t.get("agent_decisions", 0) >= 2)
            client.post(f"/api/tables/{table_id}/control", json={"action": "pause"})
        roots = []
        for table_id in ids:
            wait_for(client, table_id, lambda t: t["status"] == "paused")
            records = client.get(f"/api/tables/{table_id}/traces").json()["items"]
            assert len(records) >= 2
            assert all(
                r["table_id"] == table_id and r["status"] == "completed"
                for r in records
            )
            roots.append({r["trace_id"] for r in records})
        assert roots[0].isdisjoint(roots[1])
    assert manager.workers == {}


def test_legacy_replay_and_interrupted_session_remain_readable(tmp_path, monkeypatch):
    from wtr.game import Tournament
    from wtr.models import TournamentConfig
    from wtr.store import Store

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/legacy.sqlite")
    monkeypatch.delenv("CONTROL_TOKEN", raising=False)
    monkeypatch.setenv("WTR_PUBLIC", "false")
    store = Store()
    store.initialize()
    config = TournamentConfig().model_dump()
    game = Tournament("legacy", config)
    store.create(game.id, config)
    snapshot = game.snapshot()
    snapshot["decision"] = {
        "action": "call",
        "source": "heuristic",
        "state_version": 0,
        "summary": "Historical record",
        "hand": 1,
        "event_id": "legacy:e1",
    }
    store.save(snapshot)
    store.engine.dispose()
    with TestClient(app) as client:
        restored = next(
            t for t in client.get("/api/tables").json() if t["id"] == "legacy"
        )
        assert restored["status"] == "interrupted"
        assert "trace_id" not in restored["decision"]
        assert (
            client.get("/api/tables/legacy/history").json()[0]["decision"]
            == snapshot["decision"]
        )
        assert client.get("/api/tables/legacy/traces").json() == {
            "items": [],
            "next_cursor": None,
        }


def test_idle_live_websocket_exits_on_disconnect(tmp_path, monkeypatch):
    import asyncio
    from wtr.main import live, origins

    store = type("EmptyStore", (), {"list": lambda self: []})()
    monkeypatch.setenv("CONTROL_TOKEN", "ws-test")
    app.state.store = store
    app.state.manager = type("Manager", (), {"poll": lambda self: None})()

    class Socket:
        headers = {"origin": origins[0]}

        def __init__(self):
            self.sent = asyncio.Event()
            self.disconnect = asyncio.Event()

        async def accept(self):
            pass

        async def receive_json(self):
            return {"token": "ws-test"}

        async def receive(self):
            await self.disconnect.wait()
            return {"type": "websocket.disconnect"}

        async def send_json(self, data):
            assert data == {"type": "tables", "tables": []}
            self.sent.set()

    async def exercise():
        ws = Socket()
        task = asyncio.create_task(live(ws))
        await asyncio.wait_for(ws.sent.wait(), 2)
        ws.disconnect.set()
        await asyncio.wait_for(task, 0.5)

    asyncio.run(exercise())
