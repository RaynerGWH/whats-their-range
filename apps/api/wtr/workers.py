"""One process and one writer per table. No cross-table turn scheduler."""

import asyncio
import multiprocessing as mp
import queue
import threading
import time
import uuid
from copy import deepcopy

from .agent import Agent
from .game import Tournament
from .opponents import OpponentError, resolve_seeds
from .store import Store
from .tableplay import TablePlay, resolve_config

TERMINAL = {"finished", "stopped", "error", "interrupted"}


def table_worker(table_id, config, commands, database_url, replies=None):
    asyncio.run(_table_worker(table_id, config, commands, database_url, replies))


async def _table_worker(table_id, config, commands, database_url, replies):
    store = Store(database_url)
    config = resolve_seeds(config)
    game = Tournament(table_id, config)
    active_trace_id = None
    active_player = None
    hero_turn = None
    pending = None
    observed = None
    play = None

    def manual_turn():
        return (
            play
            and play.budget is not None
            and game.config.get("hero_control") == "human"
            and game.actor == game.hero_seat
            and game.status not in TERMINAL
        )

    def publish(replay=True):
        nonlocal hero_turn
        if replay:
            game.version += 1
        if manual_turn():
            if hero_turn is None or hero_turn["state_version"] != game.version:
                observation = play.observation()
                hero_turn = {
                    "player": game.hero_seat,
                    "state_version": game.version,
                    "chat_sequence": game.chat_sequence,
                    "turn_token": uuid.uuid4().hex,
                    "observation": observation,
                }
            game.phase = "awaiting_human"
        else:
            hero_turn = None
        snap = {
            **(play.snapshot() if play else game.snapshot()),
            "active_trace_id": active_trace_id,
            "active_player": active_player,
            "hero_turn": deepcopy(hero_turn),
        }
        store.save(snap, replay)

    def record_trace(record):
        nonlocal active_trace_id
        if record["langsmith_url"]:
            store.set_trace_url(record)
            return
        store.save_trace(record)
        next_id = record["trace_id"] if record["status"] == "running" else None
        if next_id != active_trace_id:
            active_trace_id = next_id
            publish(False)

    async def cancel_turn():
        nonlocal pending, active_player
        if pending is not None:
            pending.cancel()
            try:
                await pending
            except asyncio.CancelledError:
                pass
            pending = None
        active_player = None
        if game.phase == "thinking":
            game.phase = "playing"

    def reply(command, error=None):
        if replies is not None and command.get("request_id"):
            replies.put_nowait({"request_id": command["request_id"], "error": error})

    try:
        play = TablePlay(table_id, config, trace_sink=record_trace, agent_factory=Agent)
        game = play.game
        publish()
        due, step = time.monotonic(), False
        while game.status not in TERMINAL:
            # Drain ordered commands before accepting an in-flight result.
            for _ in range(32):
                try:
                    command = commands.get_nowait()
                except queue.Empty:
                    break
                try:
                    action = command["action"]
                    if action == "hero_action":
                        if not manual_turn() or hero_turn is None:
                            raise ValueError("No manual hero turn is pending")
                        if (
                            command["state_version"] != game.version
                            or command["turn_token"] != hero_turn["turn_token"]
                        ):
                            raise ValueError("Stale or consumed hero turn")
                        obs = deepcopy(hero_turn["observation"])
                        decision = {
                            "action": command["key"],
                            "public_message": command.get("public_message"),
                            "source": "human",
                            "model": None,
                            "player": game.hero_seat,
                            "state_version": game.version,
                            "chat_sequence": game.chat_sequence,
                            "summary": "Human selected this action.",
                            "uncertainty": "Human decision.",
                            "evidence_ids": [],
                            "observation": obs,
                            "metrics": {},
                            "evidence": [],
                            "usage": {},
                            "fallback": None,
                            "trace_id": None,
                            "latency_ms": None,
                        }
                        # apply validates everything before chips or chat can change.
                        play.apply(obs, decision)
                        hero_turn = None
                        if game.phase == "awaiting_human":
                            game.phase = "playing"
                        step = False
                        publish()
                        due = time.monotonic() + game.config["pace"]
                    elif action == "set_hero_control":
                        if (
                            play.budget is None
                            or command["state_version"] != game.version
                        ):
                            raise ValueError(
                                "Stale control switch or unsupported table"
                            )
                        await cancel_turn()
                        hero_turn = None
                        previous = game.config["hero_control"]
                        game.config["hero_control"] = command["hero_control"]
                        game.control_changes.append(
                            {
                                "state_version": game.version + 1,
                                "hand": game.hand,
                                "from": previous,
                                "to": command["hero_control"],
                            }
                        )
                        game.control_changes = game.control_changes[-100:]
                        if game.phase == "awaiting_human":
                            game.phase = "playing"
                        step = False
                        publish()
                    elif action in ("pause", "stop"):
                        await cancel_turn()
                        game.status = "paused" if action == "pause" else "stopped"
                        step = False
                        publish()
                    elif action == "resume":
                        game.status = "running"
                        publish(pending is None)
                    elif action == "step":
                        if pending is None:
                            game.status, step = "paused", True
                            publish()
                    elif action == "speed":
                        game.config["pace"] = command["pace"]
                        publish(pending is None)
                    reply(command)
                except ValueError as exc:
                    reply(command, str(exc))
            if game.status in TERMINAL:
                break
            if pending is not None and pending.done():
                decision = pending.result()
                pending = None
                game.phase = "playing"
                play.apply(observed, decision)
                active_player = None
                publish()
                due = time.monotonic() + game.config["pace"] * (
                    2 if game.phase == "hand_complete" else 1
                )
            if (
                pending is None
                and not manual_turn()
                and (step or (game.status == "running" and time.monotonic() >= due))
            ):
                step = False
                if game.phase == "hand_complete":
                    game.new_hand()
                    publish()
                else:
                    observed = play.observation()
                    active_player = observed["player"]
                    game.phase = "thinking"
                    publish(False)
                    pending = asyncio.create_task(play.decide(observed))
            await asyncio.sleep(0.01)
    except Exception as exc:
        import logging

        logging.exception("Table worker failed: %s", table_id)
        game.status, game.phase = "error", "error"
        game.error = (
            str(exc) if isinstance(exc, OpponentError) else "Table worker failed"
        )
        publish()
    finally:
        await cancel_turn()
        if play:
            play.close()
        store.engine.dispose()
        commands.close()
        if replies is not None:
            replies.close()


class TableManager:
    def __init__(self, store):
        self.store, self.ctx = store, mp.get_context("spawn")
        self.workers = {}
        self.replies, self.request_locks = {}, {}
        self.lock = threading.RLock()

    def create(self, config):
        config = resolve_config(config, credentials=True)
        with self.lock:
            self.poll()
            if len(self.workers) >= 2:
                raise ValueError(
                    "Two live tables are already open. Stop one to create another."
                )
            table_id = uuid.uuid4().hex[:12]
            self.store.create(table_id, config)
            commands = self.ctx.Queue(maxsize=32)
            replies = self.ctx.Queue(maxsize=32)
            process = self.ctx.Process(
                target=table_worker,
                args=(
                    table_id,
                    config,
                    commands,
                    self.store.engine.url.render_as_string(hide_password=False),
                    replies,
                ),
                daemon=True,
            )
            process.start()
            self.workers[table_id] = (process, commands)
            self.replies[table_id] = replies
            self.request_locks[table_id] = threading.Lock()
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
                    self.replies.pop(table_id).close()
                    self.request_locks.pop(table_id, None)
                    del self.workers[table_id]

    def request(self, table_id, command):
        with self.lock:
            if table_id not in self.workers:
                raise ValueError("This session is archived or no longer running.")
            lock, replies = self.request_locks[table_id], self.replies[table_id]
        with lock:
            request_id = uuid.uuid4().hex
            self.control(table_id, {**command, "request_id": request_id})
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                try:
                    result = replies.get(timeout=max(0.01, deadline - time.monotonic()))
                except queue.Empty:
                    break
                except (OSError, ValueError):
                    raise ValueError("Table worker is no longer available") from None
                if result["request_id"] == request_id:
                    if result["error"]:
                        raise ValueError(result["error"])
                    return
            raise ValueError(
                "Worker acknowledgement unavailable. Refresh the table before retrying."
            )

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
