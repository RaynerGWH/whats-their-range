"""Authenticated API and spawned production workers, with only HTTP mocked."""

import asyncio
import json
import os
import time

import httpx
import pytest
from fastapi.testclient import TestClient
from test_api import wait_for
from test_llm_table import config, reply
from wtr import workers
from wtr.main import app
from wtr.tableplay import TablePlay


async def provider(request):
    payload = json.loads(request.content)
    if payload["model"] == "mock/slow":
        await asyncio.sleep(1)
    return reply(request, message="Mock public message")


class MockPlay(TablePlay):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, transport=httpx.MockTransport(provider))


def mock_worker(*args):
    os.environ.update(LANGSMITH_TRACING="false", LANGCHAIN_TRACING_V2="false")
    workers.TablePlay = MockPlay
    workers.table_worker(*args)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/manual.sqlite")
    monkeypatch.setenv("OPENROUTER_API_KEY", "mock-only")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("CONTROL_TOKEN", "manual-test")
    monkeypatch.setenv("WTR_PUBLIC", "false")
    monkeypatch.setattr(workers, "table_worker", mock_worker)
    with TestClient(app, headers={"Authorization": "Bearer manual-test"}) as c:
        yield c
    assert not app.state.manager.workers


def create(client, **changes):
    cfg = config()
    cfg.update(hero_seat=2, hero_control="human", **changes)
    result = client.post("/api/tables", json=cfg)
    assert result.status_code == 201, result.text
    table_id = result.json()["id"]
    return table_id, wait_for(client, table_id, lambda t: t.get("version", 0) > 0)


def command(client, table_id, action, **fields):
    result = client.post(
        f"/api/tables/{table_id}/control", json={"action": action, **fields}
    )
    assert result.status_code == 202, result.text


def manual_payload(snapshot, message=None):
    turn = snapshot["hero_turn"]
    return {
        "turn_token": turn["turn_token"],
        "state_version": turn["state_version"],
        "action": next(
            a["key"] for a in turn["observation"]["legal"] if a["kind"] == "call"
        ),
        "public_message": message,
    }


def current(client, table_id):
    return next(t for t in client.get("/api/tables").json() if t["id"] == table_id)


def test_manual_atomic_validation_waiting_independence_and_paused_submit(client):
    one, a = create(client)
    two, b = create(client, seed=19)
    assert len({p.pid for p, _ in app.state.manager.workers.values()}) == 2
    assert a["hero_turn"]["player"] == 2 and a["status"] == "paused"
    payload = manual_payload(a, "Public human claim")
    path = f"/api/tables/{one}/hero-action"
    assert (
        client.post(
            path, json=payload, headers={"Authorization": "Bearer wrong"}
        ).status_code
        == 401
    )
    for change in (
        {"action": "invalid"},
        {"public_message": "x" * 241},
        {"turn_token": "x" * 32},
        {"state_version": a["version"] + 1},
    ):
        assert client.post(path, json={**payload, **change}).status_code == 409
        assert current(client, one) == a
    time.sleep(0.15)
    assert current(client, one)["provider_usage"]["total"]["attempts"] == 0
    assert client.post(path, json=payload).status_code == 202
    after = current(client, one)
    assert after["version"] == a["version"] + 1 and after["status"] == "paused"
    assert after["decision"]["source"] == "human"
    assert after["decision"]["trace_id"] is None and after["decision"]["model"] is None
    assert after["chat"][-1]["text"] == "Public human claim"
    assert client.post(path, json=payload).status_code == 409  # Duplicate/wrong turn.
    assert current(client, one) == after
    assert current(client, two) == b
    command(client, two, "resume")
    waiting = wait_for(client, two, lambda t: t["status"] == "running")
    time.sleep(0.15)
    assert current(client, two) == waiting  # No timeout fallback while waiting.
    start = time.monotonic()
    command(client, two, "stop")
    wait_for(client, two, lambda t: t["status"] == "stopped")
    assert time.monotonic() - start < 2
    assert client.get(f"/api/tables/{one}/traces").json()["items"] == []
    frames = client.get(f"/api/tables/{one}/history").json()
    assert frames[0]["chat"] == [] and frames[-1]["chat_sequence"] == 1


def test_takeover_cancels_inflight_attempt_then_manual_and_replay(client):
    cfg = config()["seat_configs"]
    cfg[2]["model"] = "mock/slow"
    table_id, initial = create(client, seat_configs=cfg)
    old = manual_payload(initial)
    command(
        client,
        table_id,
        "set_hero_control",
        hero_control="llm",
        state_version=initial["version"],
    )
    switched = current(client, table_id)
    assert switched["status"] == "paused" and switched["hero_turn"] is None
    assert switched["provider_usage"]["total"]["attempts"] == 0
    assert (
        client.post(f"/api/tables/{table_id}/hero-action", json=old).status_code == 409
    )
    command(client, table_id, "step")
    active = wait_for(client, table_id, lambda t: t.get("active_trace_id") is not None)
    trace_id = active["active_trace_id"]
    command(
        client,
        table_id,
        "set_hero_control",
        hero_control="human",
        state_version=active["version"],
    )
    manual = current(client, table_id)
    assert (
        manual["hero_turn"] and manual["hero_turn"]["turn_token"] != old["turn_token"]
    )
    assert manual["players"] == initial["players"] and not manual["chat"]
    assert manual["decision"] is None and manual["active_trace_id"] is None
    assert manual["provider_usage"]["by_player"]["2"]["attempts"] == 1
    assert manual["provider_usage"]["total"]["cost_usd"] is None
    trace = client.get(f"/api/tables/{table_id}/traces/{trace_id}").json()
    assert (
        trace["status"] == "cancelled" and trace["state_version"] == active["version"]
    )
    time.sleep(1.1)
    assert current(client, table_id) == manual
    assert (
        client.post(
            f"/api/tables/{table_id}/hero-action",
            json=manual_payload(manual, "Human claim"),
        ).status_code
        == 202
    )
    after = current(client, table_id)
    assert after["decision"]["source"] == "human" and after["status"] == "paused"
    command(
        client,
        table_id,
        "set_hero_control",
        hero_control="llm",
        state_version=after["version"],
    )
    stale = client.post(
        f"/api/tables/{table_id}/control",
        json={
            "action": "set_hero_control",
            "hero_control": "human",
            "state_version": after["version"],
        },
    )
    assert stale.status_code == 409
    command(client, table_id, "resume")
    final = wait_for(client, table_id, lambda t: t["status"] == "finished")
    assert sum(p["prize"] for p in final["players"]) == 100
    assert any(
        d["source"] == "openrouter" for d in final["decisions_by_player"].values()
    )
    frames = client.get(f"/api/tables/{table_id}/history", params={"limit": 200}).json()
    assert {f["config"]["hero_control"] for f in frames} == {"human", "llm"}
    assert len(final["control_changes"]) == 3
    for frame in frames:
        assert all(
            m["sequence"] <= frame["chat_sequence"]
            and m["state_version"] < frame["version"]
            for m in frame["chat"]
        )
        assert sum(p["stack"] for p in frame["players"]) + frame["pot"] == 600
    traces = client.get(
        f"/api/tables/{table_id}/traces", params={"player": 2, "limit": 1}
    ).json()
    assert traces["items"] and all(
        t["metadata"]["player"] == 2 for t in traces["items"]
    )
    if traces["next_cursor"]:
        assert (
            client.get(
                f"/api/tables/{table_id}/traces",
                params={"player": 1, "cursor": traces["next_cursor"]},
            ).status_code
            == 400
        )
    assert (
        client.get(f"/api/tables/{table_id}/traces", params={"player": 6}).status_code
        == 422
    )


@pytest.mark.parametrize("action", ["pause", "stop"])
def test_inflight_llm_controls_cancel_without_committing(client, action):
    cfg = config()["seat_configs"]
    cfg[2]["model"] = "mock/slow"
    table_id, initial = create(client, seat_configs=cfg)
    command(
        client,
        table_id,
        "set_hero_control",
        hero_control="llm",
        state_version=initial["version"],
    )
    command(client, table_id, "resume")
    active = wait_for(client, table_id, lambda t: t.get("active_trace_id"))
    command(client, table_id, action)
    final = wait_for(
        client,
        table_id,
        lambda t: t["status"] == ("paused" if action == "pause" else "stopped"),
    )
    assert final["players"] == initial["players"] and not final["chat"]
    assert (
        final["decision"] is None and final["provider_usage"]["total"]["attempts"] == 1
    )
    assert (
        client.get(f"/api/tables/{table_id}/traces/{active['active_trace_id']}").json()[
            "status"
        ]
        == "cancelled"
    )
