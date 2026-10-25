"""One process and one writer per table. No cross-table turn scheduler."""

import asyncio
import multiprocessing as mp
import queue
import time
import uuid

from .agent import Agent, assess, baseline
from .game import Tournament, PROFILES
from .store import Store

TERMINAL = {"finished", "stopped", "error", "interrupted"}


def table_worker(table_id, config, commands, updates, database_url):
    store = Store(database_url)
    game = Tournament(table_id, config)
    agent = Agent(config["mode"], config["model"], config["seed"])

    def publish(replay=True):
        if replay:
            game.version += 1
        snap = game.snapshot()
        store.save(snap, replay)
        updates.put(snap)

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
        store.engine.dispose()


class TableManager:
    def __init__(self, store):
        self.store, self.ctx = store, mp.get_context("spawn")
        self.workers, self.latest = {}, {}

    def create(self, config):
        if sum(p.is_alive() for p, _, _ in self.workers.values()) >= 2:
            raise ValueError(
                "Two live tables are already open. Stop one to create another."
            )
        table_id = uuid.uuid4().hex[:12]
        self.store.create(table_id, config)
        commands, updates = self.ctx.Queue(), self.ctx.Queue()
        process = self.ctx.Process(
            target=table_worker,
            args=(
                table_id,
                config,
                commands,
                updates,
                str(self.store.engine.url.render_as_string(hide_password=False)),
            ),
            daemon=True,
        )
        process.start()
        self.workers[table_id] = (process, commands, updates)
        return table_id

    def poll(self):
        for table_id, (process, _, updates) in self.workers.items():
            while True:
                try:
                    self.latest[table_id] = updates.get_nowait()
                except queue.Empty:
                    break
            current = self.latest.get(table_id)
            if not process.is_alive() and (
                current is None or current["status"] not in TERMINAL
            ):
                if current:
                    current = {**current, "status": "error", "phase": "error"}
                    self.latest[table_id] = current
                    self.store.save(current, False)
        return self.latest

    def control(self, table_id, command):
        if table_id not in self.workers or not self.workers[table_id][0].is_alive():
            raise ValueError("This session is archived or no longer running.")
        self.workers[table_id][1].put(command)

    def close(self):
        for process, commands, _ in self.workers.values():
            if process.is_alive():
                commands.put({"action": "stop"})
        deadline = time.monotonic() + 12
        for process, _, _ in self.workers.values():
            process.join(max(0, deadline - time.monotonic()))
            if process.is_alive():
                process.terminate()
                process.join(2)
        self.poll()
