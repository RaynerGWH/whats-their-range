"""Versioned snapshots are also the replay log. No hidden state goes to agents."""

import base64
import json
import os
from copy import deepcopy
from pathlib import Path

from sqlalchemy import (
    JSON,
    Column,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    delete,
    select,
    text,
    update,
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

traces = Table(
    "wtr_traces",
    metadata,
    Column("sequence", Integer, primary_key=True, autoincrement=True),
    Column("trace_id", String, nullable=False, unique=True),
    Column("table_id", String, nullable=False),
    Column("hand", Integer, nullable=False),
    Column("status", String, nullable=False),
    Column("record", JSON, nullable=False),
)
Index("ix_wtr_traces_table_sequence", traces.c.table_id, traces.c.sequence)
Index(
    "ix_wtr_traces_table_hand_sequence",
    traces.c.table_id,
    traces.c.hand,
    traces.c.sequence,
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
        # Additive v1 initialization: old session/event tables are unchanged.
        # Create and secure new tables in one PostgreSQL transaction.
        with self.engine.begin() as c:
            metadata.create_all(c)
            if self.engine.dialect.name == "postgresql":
                for name in ("wtr_sessions", "wtr_events", "wtr_traces"):
                    c.execute(text(f"ALTER TABLE {name} ENABLE ROW LEVEL SECURITY"))
            # Only the API host initializes. Workers never interrupt other tables.
            c.execute(
                update(sessions)
                .where(
                    sessions.c.status.in_(["running", "paused", "starting", "thinking"])
                )
                .values(status="interrupted")
            )
            self._cancel_traces(c)

    def _cancel_traces(self, c, table_id=None):
        from .tracing import utcnow

        query = select(traces).where(traces.c.status == "running")
        if table_id is not None:
            query = query.where(traces.c.table_id == table_id)
        for row in c.execute(query).mappings().all():
            record = deepcopy(row["record"])
            record.update(status="cancelled", ended_at=utcnow())
            record["metadata"]["interrupted"] = True
            for span in record["spans"]:
                if span["status"] == "running":
                    span.update(
                        status="cancelled",
                        ended_at=record["ended_at"],
                        error={
                            "code": "Interrupted",
                            "message": "Table process interrupted",
                        },
                    )
            c.execute(
                update(traces)
                .where(traces.c.trace_id == row["trace_id"])
                .values(status="cancelled", record=record)
            )

    def interrupt(self, table_id):
        with self.engine.begin() as c:
            row = (
                c.execute(select(sessions).where(sessions.c.id == table_id))
                .mappings()
                .first()
            )
            if row and row["status"] not in {
                "finished",
                "stopped",
                "error",
                "interrupted",
            }:
                snap = {
                    **row["snapshot"],
                    "status": "error",
                    "phase": "error",
                    "active_trace_id": None,
                }
                c.execute(
                    update(sessions)
                    .where(sessions.c.id == table_id)
                    .values(status="error", snapshot=snap)
                )
            self._cancel_traces(c, table_id)

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
                "active_trace_id": None
                if r["status"] == "interrupted"
                else r["snapshot"].get("active_trace_id"),
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

    def has_table(self, table_id):
        with self.engine.connect() as c:
            return (
                c.execute(
                    select(sessions.c.id).where(sessions.c.id == table_id)
                ).first()
                is not None
            )

    def save_trace(self, record):
        from sqlalchemy.dialects.postgresql import insert as postgres_insert
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        insert = (
            postgres_insert
            if self.engine.dialect.name == "postgresql"
            else sqlite_insert
        )
        values = {
            "trace_id": record["trace_id"],
            "table_id": record["table_id"],
            "hand": record["hand"],
            "status": record["status"],
            "record": record,
        }
        statement = insert(traces).values(**values)
        statement = statement.on_conflict_do_update(
            index_elements=[traces.c.trace_id],
            set_={"status": record["status"], "record": record},
        )
        with self.engine.begin() as c:
            c.execute(statement)
            if record["status"] != "running":
                keep = max(1, int(os.getenv("TRACE_MAX_PER_TABLE", "2000")))
                old = (
                    select(traces.c.sequence)
                    .where(
                        traces.c.table_id == record["table_id"],
                        traces.c.status != "running",
                    )
                    .order_by(traces.c.sequence.desc())
                    .offset(keep)
                )
                c.execute(delete(traces).where(traces.c.sequence.in_(old)))

    def set_trace_url(self, record):
        # Export completion updates only the link, never overwrites newer local spans
        # or resurrects a trace removed by retention.
        with self.engine.begin() as c:
            existing = c.execute(
                select(traces.c.record).where(traces.c.trace_id == record["trace_id"])
            ).scalar_one_or_none()
            if existing:
                existing["langsmith_url"] = record["langsmith_url"]
                c.execute(
                    update(traces)
                    .where(traces.c.trace_id == record["trace_id"])
                    .values(record=existing)
                )

    def get_trace(self, table_id, trace_id):
        with self.engine.connect() as c:
            return c.execute(
                select(traces.c.record).where(
                    traces.c.table_id == table_id, traces.c.trace_id == trace_id
                )
            ).scalar_one_or_none()

    def list_traces(self, table_id, hand=None, limit=50, cursor=None):
        query = select(traces).where(traces.c.table_id == table_id)
        if hand is not None:
            query = query.where(traces.c.hand == hand)
        if cursor:
            try:
                value = json.loads(
                    base64.b64decode(cursor.encode(), altchars=b"-_", validate=True)
                )
                if (
                    not isinstance(value, list)
                    or len(value) != 3
                    or value[:2] != [table_id, hand]
                    or type(value[2]) is not int
                    or not 1 <= value[2] <= 2**63 - 1
                ):
                    raise ValueError
                query = query.where(traces.c.sequence < value[2])
            except (ValueError, UnicodeError, TypeError):
                raise ValueError("Invalid trace cursor") from None
        with self.engine.connect() as c:
            rows = (
                c.execute(query.order_by(traces.c.sequence.desc()).limit(limit + 1))
                .mappings()
                .all()
            )
        next_cursor = None
        if len(rows) > limit:
            next_cursor = base64.urlsafe_b64encode(
                json.dumps([table_id, hand, rows[limit - 1]["sequence"]]).encode()
            ).decode()
        return {
            "items": [r["record"] for r in rows[:limit]],
            "next_cursor": next_cursor,
        }
