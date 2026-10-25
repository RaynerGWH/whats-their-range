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
