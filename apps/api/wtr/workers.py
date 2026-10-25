"""One process and one writer per table. No cross-table turn scheduler."""

import asyncio
import multiprocessing as mp
import queue
import threading
import time
import uuid

from .agent import Agent, assess, baseline
from .game import PROFILES, Tournament
from .store import Store

TERMINAL = {"finished", "stopped", "error", "interrupted"}


def table_worker(table_id, config, commands, database_url):
    store = Store(database_url)
    game = Tournament(table_id, config)
    active_trace_id = None

    def publish(replay=True):
        if replay:
            game.version += 1
        snap = {**game.snapshot(), "active_trace_id": active_trace_id}
        store.save(snap, replay)

    def record_trace(record):
        nonlocal active_trace_id
        # Background export only patches the URL; it never touches game state.
        if record["langsmith_url"]:
            store.set_trace_url(record)
            return
        store.save_trace(record)
        next_id = record["trace_id"] if record["status"] == "running" else None
        if next_id != active_trace_id:
            active_trace_id = next_id
            publish(False)

    # Policy randomness must not expose or derive from the hidden deck seed.
    agent = Agent(config["mode"], config["model"], seed=42, trace_sink=record_trace)

    try:
        publish()
        due = time.monotonic()
        while game.status not in TERMINAL:
            step = False
            try:
                command = commands.get(timeout=0.03)
                action = command["action"]
                if action == "stop":
                    game.status = "stopped"
                elif action == "pause":
                    game.status = "paused"
                elif action == "resume":
                    game.status = "running"
                elif action == "step":
                    game.status = "paused"
                    step = True
                elif action == "speed":
                    game.config["pace"] = command["pace"]
                publish()
            except queue.Empty:
                pass
            if game.status in TERMINAL:
                break
            if not step and (game.status != "running" or time.monotonic() < due):
                continue
            if game.phase == "hand_complete":
                game.new_hand()
            else:
                obs = game.observation()
                if game.actor == 0:
                    game.phase = "thinking"
                    publish(False)
                    decision = asyncio.run(agent.decide(obs))
                    game.phase = "playing"
                    game.apply(decision["action"], obs["version"], decision)
                else:
                    metrics = assess({"observation": obs})["metrics"]
                    action = baseline(obs, metrics, game.rng, PROFILES[game.actor])
                    game.apply(action, obs["version"])
            publish()
            due = time.monotonic() + game.config["pace"] * (
                2 if game.phase == "hand_complete" else 1
            )
    except Exception:
        import logging

        logging.exception("Table worker failed: %s", table_id)
        game.status, game.phase = "error", "error"
        try:
            publish()
        except Exception:
            pass
    finally:
        agent.close()
        store.engine.dispose()
        commands.close()


class TableManager:
    def __init__(self, store):
        self.store, self.ctx = store, mp.get_context("spawn")
        self.workers = {}
        self.lock = threading.RLock()

    def create(self, config):
        with self.lock:
            self.poll()
            if len(self.workers) >= 2:
                raise ValueError(
                    "Two live tables are already open. Stop one to create another."
                )
            table_id = uuid.uuid4().hex[:12]
            self.store.create(table_id, config)
            commands = self.ctx.Queue(maxsize=32)
            process = self.ctx.Process(
                target=table_worker,
                args=(
                    table_id,
                    config,
                    commands,
                    self.store.engine.url.render_as_string(hide_password=False),
                ),
                daemon=True,
            )
            process.start()
            self.workers[table_id] = (process, commands)
            return table_id

    def poll(self):
        # Snapshots already live in the database. No duplicate snapshot IPC queue
        # can grow while browsers are disconnected or keep a worker alive on exit.
        with self.lock:
            for table_id, (process, commands) in list(self.workers.items()):
                if not process.is_alive():
                    process.join()
                    self.store.interrupt(table_id)
                    commands.cancel_join_thread()
                    commands.close()
                    process.close()
                    del self.workers[table_id]

    def control(self, table_id, command):
        with self.lock:
            if table_id not in self.workers or not self.workers[table_id][0].is_alive():
                raise ValueError("This session is archived or no longer running.")
            try:
                self.workers[table_id][1].put_nowait(command)
            except queue.Full:
                raise ValueError(
                    "Table control queue is full. Try again shortly."
                ) from None

    def close(self):
        with self.lock:
            for process, commands in self.workers.values():
                if process.is_alive():
                    try:
                        commands.put_nowait({"action": "stop"})
                    except queue.Full:
                        pass
            deadline = time.monotonic() + 12
            for process, _ in self.workers.values():
                process.join(max(0, deadline - time.monotonic()))
                if process.is_alive():
                    process.terminate()
                    process.join(2)
                    if process.is_alive():
                        process.kill()
                        process.join(2)
            self.poll()
