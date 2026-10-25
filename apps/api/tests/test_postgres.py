"""Opt-in verification against a disposable PostgreSQL database, never production."""

import asyncio
import os
from uuid import uuid4

import pytest
from sqlalchemy import text
from wtr.agent import Agent
from wtr.game import Tournament
from wtr.models import TournamentConfig
from wtr.store import Store


@pytest.mark.skipif(
    not os.getenv("WTR_TEST_POSTGRES_URL"),
    reason="Disposable PostgreSQL URL not supplied",
)
def test_postgres_initialization_upsert_retention_restart_and_rls(monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("TRACE_MAX_PER_TABLE", "2")
    store = Store(os.environ["WTR_TEST_POSTGRES_URL"])
    store.initialize()
    table_id = "pg-" + uuid4().hex
    config = TournamentConfig().model_dump()
    store.create(table_id, config)
    game = Tournament(table_id, config)
    store.save(game.snapshot())
    ids = []
    for _ in range(3):
        agent = Agent(trace_sink=store.save_trace)
        decision = asyncio.run(agent.decide(game.observation()))
        ids.append(decision["trace_id"])
    assert store.get_trace(table_id, ids[0]) is None
    page = store.list_traces(table_id, limit=1)
    assert page["items"][0]["trace_id"] == ids[2]
    assert (
        store.list_traces(table_id, cursor=page["next_cursor"])["items"][0]["trace_id"]
        == ids[1]
    )
    record = store.get_trace(table_id, ids[2])
    record["langsmith_url"] = "https://smith.langchain.com/test"
    store.set_trace_url(record)
    assert store.get_trace(table_id, ids[2])["langsmith_url"] == record["langsmith_url"]
    with store.engine.begin() as connection:
        secured = (
            connection.execute(
                text(
                    "SELECT relname FROM pg_class WHERE relrowsecurity AND relname LIKE 'wtr_%'"
                )
            )
            .scalars()
            .all()
        )
        assert set(secured) == {"wtr_sessions", "wtr_events", "wtr_traces"}
        # An ordinary role with SELECT grants still cannot read private records.
        connection.execute(text("CREATE ROLE wtr_trace_test_reader NOLOGIN"))
        connection.execute(
            text(
                "GRANT SELECT ON wtr_sessions, wtr_events, wtr_traces TO wtr_trace_test_reader"
            )
        )
        connection.execute(text("SET LOCAL ROLE wtr_trace_test_reader"))
        for name in secured:
            assert (
                connection.execute(text(f"SELECT count(*) FROM {name}")).scalar_one()
                == 0
            )
        connection.execute(text("RESET ROLE"))
        connection.execute(
            text(
                "REVOKE SELECT ON wtr_sessions, wtr_events, wtr_traces FROM wtr_trace_test_reader"
            )
        )
        connection.execute(text("DROP ROLE wtr_trace_test_reader"))
    store.engine.dispose()
    store = Store(os.environ["WTR_TEST_POSTGRES_URL"])
    store.initialize()
    assert len(store.list_traces(table_id)["items"]) == 2
    assert store.history(table_id)
    assert (
        next(t for t in store.list() if t["id"] == table_id)["status"] == "interrupted"
    )
    store.engine.dispose()
