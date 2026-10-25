"""Bounded, private execution records. No spectator state or ambient SDK traces."""

import json
import logging
import math
import os
import queue
import re
import threading
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from datetime import datetime, timezone

current_trace = ContextVar("wtr_trace", default=None)
current_span = ContextVar("wtr_span", default=None)
MAX_JSON_BYTES = 131072


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def clean(value, depth=0):
    """Defence in depth after explicit observation/provider allowlists."""
    if depth > 16:
        return "[truncated]"
    if isinstance(value, dict):
        forbidden = {
            "cards",
            "profile",
            "profiles",
            "archetype",
            "deck",
            "headers",
            "authorization",
            "api_key",
            "password",
            "secret",
            "reasoning",
            "reasoning_details",
            "raw",
            "body",
        }
        return {
            str(k)[:100]: clean(v, depth + 1)
            for k, v in list(value.items())[:200]
            if str(k).lower() not in forbidden
        }
    if isinstance(value, list):
        return [clean(v, depth + 1) for v in value[:200]]
    if isinstance(value, str):
        for name in (
            "OPENROUTER_API_KEY",
            "LANGSMITH_API_KEY",
            "CONTROL_TOKEN",
            "DATABASE_URL",
        ):
            secret = os.getenv(name)
            if secret:
                value = value.replace(secret, "[redacted]")
        return value[:65536]
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    return None


def bounded(value):
    result = clean(value)
    if len(json.dumps(result).encode()) > MAX_JSON_BYTES:
        return {"truncated": True, "reason": "Trace payload size limit"}
    return result


def private_observation(obs):
    """Rebuild the permitted schema even if a caller adds spectator fields."""
    scalar = "table_id hand version player position hole board street pot to_call big_blind hand_start_stacks payouts".split()
    result = {k: deepcopy(obs[k]) for k in scalar if k in obs}
    fields = {
        "players": "seat stack bet active position",
        "legal": "key kind amount",
        "history": "id hand street text player action amount",
        "opponents": "seat name actions raises folds calls",
    }
    for name, keys in fields.items():
        result[name] = [
            {k: deepcopy(row[k]) for k in keys.split() if k in row}
            for row in obs.get(name, [])
        ]
    result["history"] = public_events(obs.get("history", []))
    for source, target in zip(obs.get("opponents", []), result["opponents"]):
        target["name"] = f"Player {target['seat'] + 1}"
        target["recent_actions"] = public_events(source.get("recent_actions", [])[-5:])
    if "chat" in obs:
        chat = obs["chat"]
        cutoff = chat.get("last_sequence", 0)
        if type(cutoff) is not int or cutoff < 0:
            raise ValueError("Invalid chat cutoff")
        messages = []
        for row in chat.get("messages", [])[-100:]:
            if (
                type(row.get("sequence")) is int
                and 0 < row["sequence"] <= cutoff
                and row.get("id") == f"c{row['sequence']}"
                and type(row.get("player")) is int
                and 0 <= row["player"] < 6
                and type(row.get("hand")) is int
                and 1 <= row["hand"] <= obs["hand"]
                and type(row.get("state_version")) is int
                and 0 <= row["state_version"] <= obs["version"]
                and isinstance(row.get("text"), str)
                and 1 <= len(row["text"]) <= 500
                and not any(ord(c) < 32 for c in row["text"])
                and (not messages or row["sequence"] > messages[-1]["sequence"])
            ):
                messages.append(
                    {
                        k: deepcopy(row[k])
                        for k in (
                            "id",
                            "sequence",
                            "player",
                            "hand",
                            "state_version",
                            "text",
                        )
                    }
                )
        result["chat"] = {
            "last_sequence": cutoff,
            "messages": messages,
            "truncated": bool(chat.get("truncated", False)),
        }
    return clean(result)


def public_events(events):
    """Reconstruct public action text and local evidence IDs, never copy prose."""
    result = []
    for event in events:
        match = re.fullmatch(r"(?:.*:)?e([1-9][0-9]{0,9})", str(event.get("id", "")))
        action, seat = event.get("action"), event.get("player")
        if (
            not match
            or type(seat) is not int
            or not 0 <= seat < 6
            or not isinstance(action, str)
            or not re.fullmatch(r"fold|check|call|raise:[0-9]+", action)
        ):
            continue
        amount = event.get("amount", 0)
        if type(amount) is not int or amount < 0:
            continue
        words = "raises to" if action.startswith("raise:") else action + "s"
        result.append(
            {
                "id": "e" + match[1],
                "hand": event["hand"],
                "street": event["street"],
                "player": seat,
                "action": action,
                "amount": amount,
                "text": f"Player {seat + 1} {words}{' ' + str(amount) if amount else ''}.",
            }
        )
    return result


def usage_from_provider(raw):
    raw = raw if isinstance(raw, dict) else {}

    def number(key, integer=False):
        v = raw.get(key)
        valid = type(v) is int if integer else type(v) in (int, float)
        return v if valid and math.isfinite(v) and v >= 0 else None

    return {
        "input_tokens": number("prompt_tokens", True),
        "output_tokens": number("completion_tokens", True),
        "cost_usd": number("cost"),
    }


class Trace:
    def __init__(self, observation, sink=None):
        self.sink = sink
        self.lock = threading.RLock()
        self.clock = time.perf_counter()
        self.record = {
            "schema_version": 1,
            "trace_id": str(uuid.uuid4()),
            "table_id": observation["table_id"],
            "hand": observation["hand"],
            "state_version": observation["version"],
            "status": "running",
            "started_at": utcnow(),
            "ended_at": None,
            "duration_ms": None,
            "langsmith_url": None,
            "spans": [],
            "metadata": {
                "player": observation["player"],
                "chat_sequence": observation.get("chat", {}).get("last_sequence", 0),
            },
        }

    def emit(self):
        if self.sink:
            try:
                self.sink(deepcopy(self.record))
            except Exception:
                # Local tracing must not change the legal action or stop the table.
                self.record["metadata"]["persistence_failed"] = True

    @contextmanager
    def span(self, name, kind="chain", inputs=None, model=None, root=False):
        with self.lock:
            start = self.clock if root else time.perf_counter()
            span = {
                "span_id": self.record["trace_id"] if root else str(uuid.uuid4()),
                "parent_span_id": None if root else current_span.get(),
                "name": name,
                "kind": kind,
                "status": "running",
                "started_at": self.record["started_at"] if root else utcnow(),
                "ended_at": None,
                "start_offset_ms": (start - self.clock) * 1000,
                "duration_ms": None,
                "inputs": bounded(inputs or {}),
                "outputs": None,
                "model": model,
                "usage": None,
                "error": None,
                "metadata": {},
            }
            self.record["spans"].append(span)
            self.emit()
        token = current_span.set(span["span_id"])
        status, error = "completed", None
        try:
            yield span
        except BaseException as exc:
            import asyncio

            status = "cancelled" if isinstance(exc, asyncio.CancelledError) else "error"
            error = {
                "code": type(exc).__name__,
                "message": "Execution cancelled"
                if status == "cancelled"
                else "Execution failed",
            }
            raise
        finally:
            current_span.reset(token)
            with self.lock:
                span["status"], span["error"] = status, error
                span["ended_at"] = utcnow()
                span["duration_ms"] = (time.perf_counter() - start) * 1000
                span["outputs"] = (
                    bounded(span["outputs"]) if span["outputs"] is not None else None
                )
                if root:
                    for key in ("status", "ended_at", "duration_ms"):
                        self.record[key] = span[key]
                self.emit()


def traced_node(name, kind, fn):
    def run(state):
        with current_trace.get().span(
            name, kind, {"observation": state["observation"]}
        ) as span:
            result = fn(state)
            span["outputs"] = result
            return result

    return run


class LangSmithExporter:
    """One bounded queue/thread per table. SDK network work never runs on a turn."""

    def __init__(self, sink=None, client_factory=None, capacity=16):
        self.sink = sink
        self.client_factory = client_factory
        self.queue = queue.Queue(maxsize=capacity)
        self.stopping = threading.Event()
        self.dropped = 0
        self.thread = threading.Thread(
            target=self._run, daemon=True, name="wtr-telemetry"
        )
        self.thread.start()

    def submit(self, record):
        try:
            self.queue.put_nowait(deepcopy(record))
        except queue.Full:
            self.dropped += 1

    def close(self, timeout=0.25):
        self.stopping.set()
        self.thread.join(timeout)

    def _run(self):
        # The SDK can log raw HTTP errors. Suppress only logs emitted by this
        # exporter thread, without changing logging in gameplay or other threads.
        class ExportThreadFilter(logging.Filter):
            def __init__(self):
                super().__init__()
                self.thread_id = threading.get_ident()

            def filter(self, record):
                return record.thread != self.thread_id

        log_filter = ExportThreadFilter()
        loggers = [
            logging.getLogger(name)
            for name in (
                "langsmith.client",
                "langsmith.run_trees",
                "langsmith.utils",
                "langsmith._internal._background_thread",
                "httpx",
                "httpx2",
            )
        ]
        for logger in loggers:
            logger.addFilter(log_filter)
        client = None
        try:
            while not self.stopping.is_set() or not self.queue.empty():
                try:
                    record = self.queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                try:
                    if client is None:
                        from langsmith import Client
                        from urllib3.util import Retry

                        client = (
                            self.client_factory()
                            if self.client_factory
                            else Client(
                                auto_batch_tracing=False,
                                timeout_ms=2000,
                                retry_config=Retry(total=0),
                                omit_traced_runtime_info=True,
                            )
                        )
                    self.export(client, record)
                except Exception:
                    # Never log upstream exceptions: they can include credentials.
                    pass
                finally:
                    self.queue.task_done()
        finally:
            try:
                if client:
                    client.close(timeout=0)
            except Exception:
                pass
            finally:
                for logger in loggers:
                    logger.removeFilter(log_filter)

    def export(self, client, record):
        from langsmith.run_trees import RunTree

        runs = {}
        project = os.getenv("LANGSMITH_PROJECT", "whats-their-range")
        for span in record["spans"]:
            outputs = deepcopy(span["outputs"] or {})
            metadata = {
                "table_id": record["table_id"],
                "hand": record["hand"],
                "state_version": record["state_version"],
            }
            if span["kind"] == "llm":
                metadata.update(
                    ls_provider="openrouter",
                    ls_model_name=span["model"],
                    ls_model_type="chat",
                )
                outputs = {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": json.dumps(outputs),
                            }
                        }
                    ]
                }
                usage = span["usage"]
                if usage:
                    outputs["usage_metadata"] = {
                        k: v
                        for k, v in usage.items()
                        if v is not None and k != "cost_usd"
                    }
                    if usage["cost_usd"] is not None:
                        outputs["usage_metadata"]["total_cost"] = usage["cost_usd"]
            run = RunTree(
                id=span["span_id"],
                name=span["name"],
                run_type=span["kind"],
                parent_run=runs.get(span["parent_span_id"]),
                client=client,
                project_name=project,
                start_time=datetime.fromisoformat(span["started_at"]),
                end_time=datetime.fromisoformat(span["ended_at"]),
                inputs=span["inputs"],
                outputs=outputs,
                extra={"metadata": metadata},
                error=span["error"]["message"] if span["error"] else None,
            )
            runs[span["span_id"]] = run
            run.post()
        record["langsmith_url"] = runs[record["trace_id"]].get_url()
        if self.sink:
            self.sink(record)
