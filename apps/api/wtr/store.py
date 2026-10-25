"""Versioned snapshots are also the replay log. No hidden state goes to agents."""

import os
from pathlib import Path
from sqlalchemy import (
    JSON,
    Column,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    select,
    update,
    text,
)

metadata = MetaData()
sessions = Table(
    "wtr_sessions",
    metadata,
    Column("id", String, primary_key=True),
    Column("config", JSON, nullable=False),
    Column("status", String, nullable=False),
    Column("snapshot", JSON, nullable=False),
)
events = Table(
    "wtr_events",
    metadata,
    Column("table_id", String, primary_key=True),
    Column("version", Integer, primary_key=True),
    Column("hand", Integer, nullable=False),
    Column("snapshot", JSON, nullable=False),
)


class Store:
    def __init__(self, url=None):
        url = url or os.getenv("DATABASE_URL", "sqlite:///./data/wtr.sqlite")
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        if url.startswith("sqlite:///"):
            Path(url.removeprefix("sqlite:///")).parent.mkdir(
                parents=True, exist_ok=True
            )
        self.engine = create_engine(
            url,
            pool_pre_ping=True,
            connect_args={"check_same_thread": False, "timeout": 30}
            if url.startswith("sqlite")
            else {},
        )

    def initialize(self):
        metadata.create_all(self.engine)
        if self.engine.dialect.name == "postgresql":
            with self.engine.begin() as c:
                c.execute(text("ALTER TABLE wtr_sessions ENABLE ROW LEVEL SECURITY"))
                c.execute(text("ALTER TABLE wtr_events ENABLE ROW LEVEL SECURITY"))
        # A restarted host does not silently resume old games or spend API credit.
        with self.engine.begin() as c:
            c.execute(
                update(sessions)
                .where(
                    sessions.c.status.in_(["running", "paused", "starting", "thinking"])
                )
                .values(status="interrupted")
            )

    def create(self, table_id, config):
        with self.engine.begin() as c:
            c.execute(
                sessions.insert().values(
                    id=table_id, config=config, status="starting", snapshot={}
                )
            )

    def save(self, snapshot, replay=True):
        with self.engine.begin() as c:
            c.execute(
                update(sessions)
                .where(sessions.c.id == snapshot["id"])
                .values(
                    status=snapshot["status"],
                    snapshot=snapshot,
                    config=snapshot["config"],
                )
            )
            if replay:
                c.execute(
                    events.insert().values(
                        table_id=snapshot["id"],
                        version=snapshot["version"],
                        hand=snapshot["hand"],
                        snapshot=snapshot,
                    )
                )

    def list(self):
        with self.engine.connect() as c:
            rows = c.execute(select(sessions)).mappings().all()
        return [
            {
                **r["snapshot"],
                "id": r["id"],
                "config": r["config"],
                "status": r["status"],
            }
            for r in rows
        ]

    def history(self, table_id, before=2**31 - 1, limit=100):
        with self.engine.connect() as c:
            rows = (
                c.execute(
                    select(events.c.snapshot)
                    .where(events.c.table_id == table_id, events.c.version < before)
                    .order_by(events.c.version.desc())
                    .limit(limit)
                )
                .scalars()
                .all()
            )
        return list(reversed(rows))
