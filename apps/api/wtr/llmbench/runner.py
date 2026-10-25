"""One spawned owner per run; no second engine or policy implementation."""

import asyncio
import json
import math
import multiprocessing as mp
import os
import platform
import statistics
import time
import uuid
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import httpx

from ..players import ProviderBudget
from ..tableplay import TablePlay
from .manifest import Manifest, digest, expand


class MockProvider:
    """Artificial test actions establish engineering behavior, not playing strength."""

    def __init__(self, failure=None):
        self.calls = 0
        self.failure = failure

    async def __call__(self, request):
        self.calls += 1
        payload = json.loads(request.content)
        context = json.loads(payload["messages"][1]["content"])
        obs = context["observation"]
        if self.failure == "http" and self.calls == 1:
            return httpx.Response(503, text="Mock provider unavailable")
        if self.failure == "timeout" and self.calls == 1:
            await asyncio.sleep(360)
        action = (
            obs["legal"][-1]["key"]
            if obs["hand"] % 3 == 0
            else next(a["key"] for a in obs["legal"] if a["kind"] == "call")
        )
        if self.failure == "invalid" and self.calls == 1:
            action = "invalid"
        message = (
            None
            if "Table talk is disabled." in payload["messages"][0]["content"]
            else "Mock public claim."
        )
        value = {
            "action": action,
            "summary": "Mock engineering action.",
            "uncertainty": "No strategic evidence.",
            "evidence_ids": [],
            "public_message": message,
        }
        result = {"choices": [{"message": {"content": json.dumps(value)}}]}
        if self.failure != "missing_usage":
            result["usage"] = {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "cost": 0.0001,
            }
        return httpx.Response(200, json=result)


def initial_result(run):
    return {
        **deepcopy(run),
        "status": "starting",
        "completed": False,
        "actions": 0,
        "hands": 0,
        "outcomes": None,
        "provisional_outcomes": None,
        "accepted_actions": [],
        "chat": [],
        "fallback_reasons": {},
        "rejected_actions": 0,
        "latency_ms": [],
        "duration_seconds": 0,
        "usage": ProviderBudget(
            run["config"]["llm_limits"], run["config"]["player_count"]
        ).snapshot(),
        "usage_complete": False,
        "error": None,
        "chip_conservation": None,
    }


async def run_game(run, mock=True, failure=None, progress=None):
    if run["config"].get("hero_control") != "llm":
        raise ValueError(
            "Human or mixed-control games cannot enter an autonomous benchmark"
        )
    result = initial_result(run)
    transport = httpx.MockTransport(MockProvider(failure)) if mock else None
    play = TablePlay(
        uuid.uuid4().hex, run["config"], transport=transport, export_traces=False
    )
    game = play.game
    game.status = "running"
    game.version += 1
    start = time.monotonic()
    limits = run["stopping"]

    def capture(status):
        result.update(
            status=status,
            completed=game.status == "finished"
            and status in ("completed", "completed_with_fallbacks", "budget_exhausted"),
            hands=game.hand,
            duration_seconds=round(time.monotonic() - start, 4),
            usage=play.budget.snapshot(),
        )
        snapshot = play.snapshot()
        outcome = [
            {k: p[k] for k in ("seat", "place", "prize", "stack")}
            for p in snapshot["players"]
        ]
        result["unsettled_pot"] = snapshot["pot"]
        conserved = sum(p["stack"] for p in outcome) + snapshot[
            "pot"
        ] == game.total and all(p["stack"] >= 0 for p in outcome)
        result["chip_conservation"] = (
            conserved and result["chip_conservation"] is not False
        )
        result["provisional_outcomes"] = outcome
        result["outcomes"] = outcome if result["completed"] else None
        result["usage_complete"] = status != "running"
        if progress:
            progress(deepcopy(result))

    # Checkpoint attempt reservations before requests complete, so a killed run
    # retains started attempts. No prompts or observations go to the controller.
    def trace_progress(record):
        if record["status"] == "running" and any(
            s["name"] == "model_call" for s in record["spans"]
        ):
            capture("running")

    for policy in play.policies.values():
        policy.trace_sink = trace_progress
    try:
        async with asyncio.timeout(limits["timeout_seconds"]):
            while game.status != "finished":
                if game.control_changes or game.config["hero_control"] != "llm":
                    raise ValueError("Mixed control is excluded")
                if result["actions"] >= limits["max_actions"]:
                    capture("action_limit")
                    break
                if game.phase == "hand_complete":
                    if game.hand >= limits["max_hands"]:
                        capture("hand_limit")
                        break
                    game.new_hand()
                    game.version += 1
                    continue
                obs = play.observation()
                decision = await play.decide(obs)
                try:
                    play.apply(obs, decision)
                except ValueError:
                    result["rejected_actions"] += 1
                    raise
                game.version += 1
                result["actions"] += 1
                result["accepted_actions"].append(
                    {
                        k: decision[k]
                        for k in (
                            "player",
                            "state_version",
                            "action",
                            "source",
                            "fallback",
                            "chat_sequence",
                        )
                    }
                )
                result["accepted_actions"][-1].update(
                    hand=obs["hand"], legal_keys=[a["key"] for a in obs["legal"]]
                )
                result["latency_ms"].append(decision["latency_ms"])
                if decision["fallback"]:
                    reasons = result["fallback_reasons"]
                    reasons[decision["fallback"]] = (
                        reasons.get(decision["fallback"], 0) + 1
                    )
                if decision.get("public_message") is not None:
                    result["chat"].append(deepcopy(game.chat[-1]))
                if play.budget.snapshot()["total"]["budget_exhausted"]:
                    capture("budget_exhausted")
                    break
                capture("running")
                if not result["chip_conservation"]:
                    raise RuntimeError("Chip conservation failed")
            else:
                capture(
                    "completed_with_fallbacks"
                    if result["fallback_reasons"]
                    else "completed"
                )
    except TimeoutError:
        capture("timeout")
    except Exception as exc:
        result["error"] = {
            "code": type(exc).__name__,
            "message": "Run failed; no complete outcome is claimed",
        }
        capture("error")
    finally:
        play.close()
    result["outcome_sha256"] = digest(
        {
            k: result[k]
            for k in (
                "status",
                "actions",
                "hands",
                "outcomes",
                "accepted_actions",
                "chat",
                "fallback_reasons",
                "usage",
            )
        }
    )
    return result


def _child(send, run, mock, failure):
    # Explicitly offline instrumentation for benchmark mocks. Reports, not a
    # remote tracing workspace, are the artifact of this small runner.
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    try:
        result = asyncio.run(
            run_game(run, mock, failure, lambda r: send.send(("progress", r)))
        )
        send.send(("final", result))
    except Exception as exc:
        result = initial_result(run)
        result.update(
            status="error",
            error={
                "code": type(exc).__name__,
                "message": "Worker failed before a complete result",
            },
        )
        send.send(("final", result))
    finally:
        send.close()


def isolated_run(run, mock=True, failure=None):
    ctx = mp.get_context("spawn")
    receive, send = ctx.Pipe(duplex=False)
    process = ctx.Process(target=_child, args=(send, run, mock, failure))
    result = initial_result(run)
    process.start()
    send.close()
    # Allow interpreter startup, but retain a hard outer deadline if execution
    # stops yielding to the asyncio deadline.
    deadline = time.monotonic() + run["stopping"]["timeout_seconds"] + 5
    final = False
    try:
        while time.monotonic() < deadline:
            if receive.poll(0.05):
                try:
                    kind, result = receive.recv()
                except EOFError:
                    break
                if kind == "final":
                    final = True
                    break
            elif not process.is_alive():
                break
        if not final:
            result.update(
                status="timeout" if process.is_alive() else "worker_error",
                completed=False,
                outcomes=None,
                usage_complete=False,
                error={
                    "code": "WorkerIncomplete",
                    "message": "Last checkpoint only; later usage may be unavailable",
                },
            )
    finally:
        if process.is_alive() and not final:
            process.terminate()
        process.join(2)
        if process.is_alive():
            process.kill()
            process.join(2)
        process.close()
        receive.close()
    return result


def summarize(results):
    groups = defaultdict(list)
    for run in results:
        groups[(run["preset"], run["split"])].append(run)
    summary = []
    for (preset, split), rows in groups.items():
        seeds = defaultdict(list)
        for row in rows:
            seeds[(row["seed_set"]["deck"], row["seed_set"]["policy"])].append(row)
        # Rotations share seeds. Average within each complete seed cluster first,
        # rather than pretending correlated rotations are independent samples.
        values = [
            statistics.mean(
                r["outcomes"][r["config"]["hero_seat"]]["prize"] for r in cluster
            )
            for cluster in seeds.values()
            if all(r["status"] == "completed" for r in cluster)
        ]
        mean = statistics.mean(values) if values else None
        interval = None
        if len(values) > 1:
            margin = 1.96 * statistics.stdev(values) / math.sqrt(len(values))
            interval = [max(0, mean - margin), min(100, mean + margin)]
        summary.append(
            {
                "preset": preset,
                "split": split,
                "runs": len(rows),
                "statuses": dict(Counter(r["status"] for r in rows)),
                "independent_seed_sets": len(seeds),
                "complete_provider_only_seed_sets": len(values),
                "hero_prize_mean_complete_provider_only": mean,
                "approximate_95pct_normal_interval": interval,
                "uncertainty_note": "Seed-cluster approximation; small samples are unreliable. Failures and fallbacks are retained but excluded from provider-only prize estimates.",
            }
        )
    return summary


def evaluate(manifest, mock=True, failure=None):
    manifest = Manifest.model_validate(manifest)
    if failure not in (None, "http", "invalid", "timeout", "missing_usage") or (
        failure and not mock
    ):
        raise ValueError("Failure injection requires a recognized mock scenario")
    if not mock and not os.getenv("OPENROUTER_API_KEY"):
        raise ValueError("Live runs require a backend OPENROUTER_API_KEY")
    results = [isolated_run(r, mock, failure) for r in expand(manifest)]
    sources = sorted(Path(__file__).resolve().parents[1].rglob("*.py")) + sorted(
        Path(__file__).resolve().parents[1].glob("prompts/*.txt")
    )
    return {
        "schema_version": "llm-benchmark-report-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "runtime": {
            "python": platform.python_version(),
            **{
                package: version(package)
                for package in ("pokerkit", "httpx", "langgraph", "pydantic")
            },
        },
        "mocked": mock,
        "mock_failure": failure,
        "purpose": "Engineering evidence only; no inference about model strength or chat effects"
        if mock
        else "Controlled autonomous tournament observations",
        "manifest": manifest.model_dump(),
        "manifest_sha256": digest(manifest.model_dump()),
        "source_sha256": digest(
            {
                str(p.relative_to(Path(__file__).resolve().parents[1])): p.read_text()
                for p in sources
            }
        ),
        "results": results,
        "summary": summarize(results),
    }
