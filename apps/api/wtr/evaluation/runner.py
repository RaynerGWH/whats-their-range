"""Seeded evaluation with one spawned owner per tournament and bounded execution."""

import asyncio
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import inspect
import json
import math
import multiprocessing as mp
from pathlib import Path
import platform
from importlib.metadata import version
import time

from wtr.game import Tournament
from wtr.models import TournamentConfig
from .policies import POLICIES, SCENARIOS, PolicySpec, opponent_action


@dataclass(frozen=True)
class EvaluationConfig:
    tuning_seeds: tuple[int, ...] = (1,)
    held_out_seeds: tuple[int, ...] = (101,)
    repeats: int = 1
    policies: tuple[PolicySpec, ...] = (POLICIES["heuristic"],)
    scenarios: tuple[str, ...] = ("standard",)
    opponent_profiles: tuple[str, ...] = ("tight", "caller", "aggressive", "balanced", "volatile")
    stack_bb: int = 10
    hands_per_level: int = 2
    payouts: str = "70/30"
    max_hands: int = 300
    max_actions: int = 5000
    timeout_seconds: float = 120

    def __post_init__(self):
        seeds = self.tuning_seeds + self.held_out_seeds
        if not seeds or any(type(s) is not int or not 0 <= s <= 2**31 - 1 for s in seeds):
            raise ValueError("Provide at least one integer seed between 0 and 2147483647")
        if set(self.tuning_seeds) & set(self.held_out_seeds):
            raise ValueError("Tuning and held-out seeds must be disjoint")
        if any(len(s) != len(set(s)) for s in (self.tuning_seeds, self.held_out_seeds)):
            raise ValueError("Use repeats for repeated seeds, not duplicate split entries")
        if any(type(n) is not int or n < 1 for n in (self.repeats, self.max_hands, self.max_actions)):
            raise ValueError("Repeats, max_hands and max_actions must be positive integers")
        if not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be finite and positive")
        if not self.policies or len({p.name for p in self.policies}) != len(self.policies):
            raise ValueError("Provide policies with unique names")
        if not self.scenarios or any(s not in SCENARIOS for s in self.scenarios):
            raise ValueError(f"Scenarios must be selected from {SCENARIOS}")
        if len(set(self.scenarios)) != len(self.scenarios):
            raise ValueError("Scenarios must be unique")
        profiles = {"tight", "caller", "aggressive", "balanced", "volatile"}
        if len(self.opponent_profiles) != 5 or any(p not in profiles for p in self.opponent_profiles):
            raise ValueError("Provide five supported opponent profiles for seats 1 to 5")
        TournamentConfig(stack_bb=self.stack_bb, hands_per_level=self.hands_per_level, payouts=self.payouts)


def _chip_total(game):
    if game.state.status:
        return sum(game.state.stacks) + game.state.total_pot_amount
    return sum(game.stacks)


class EvaluationFailure(Exception):
    pass


def _worker(send, config, spec, seed, scenario, table_id):
    # No graph, provider adapter, telemetry export, database, or spectator snapshot.
    game = None
    actions = 0
    stage = "policy_initialization"
    try:
        policy = spec.build(seed)
        stage = "engine"
        game = Tournament(table_id, TournamentConfig(
            seed=seed, stack_bb=config.stack_bb,
            hands_per_level=config.hands_per_level, payouts=config.payouts,
        ).model_dump())
        game.version += 1  # Initial committed state, matching the worker convention.
        while True:
            total = _chip_total(game)
            progress = {"hands": game.hand, "actions": actions,
                        "chip_total": total, "expected_chip_total": game.total,
                        "state_version": game.version}
            send.send(("progress", progress))
            if total != game.total:
                raise EvaluationFailure("chip_conservation")
            if game.status == "finished":
                if not math.isclose(sum(game.prizes), 100):
                    raise EvaluationFailure("payout_conservation")
                send.send(("complete", {"finishing_position": game.places[0],
                                        "prize_units": game.prizes[0],
                                        "places": game.places, "prizes": game.prizes}))
                return
            if game.phase == "hand_complete":
                if game.hand >= config.max_hands:
                    raise EvaluationFailure("hand_limit")
                game.new_hand()
                game.version += 1
                continue
            if actions >= config.max_actions:
                raise EvaluationFailure("action_limit")
            obs = game.observation()
            observed_version = obs["version"]
            legal = [a["key"] for a in obs["legal"]]
            actor = obs["player"]
            start = time.perf_counter()
            if actor == 0:
                stage = "policy_decision"
                decision = policy.decide(deepcopy(obs))
                if inspect.isawaitable(decision):
                    decision = asyncio.run(decision)
                if not isinstance(decision, dict) or not isinstance(decision.get("action"), str):
                    raise EvaluationFailure("invalid_policy_response")
                if type(decision.get("state_version")) is not int or decision["state_version"] != observed_version:
                    raise EvaluationFailure("stale_policy_response")
                key = decision["action"]
            else:
                stage = "opponent_decision"
                key = opponent_action(obs, scenario, config.opponent_profiles[actor - 1], game.rng)
            latency = (time.perf_counter() - start) * 1000
            if key not in legal:
                raise EvaluationFailure("illegal_policy_action")
            stage = "engine"
            game.apply(key, observed_version)
            game.version += 1
            actions += 1
            send.send(("action", {"hand": obs["hand"], "state_version": observed_version,
                                  "player": actor, "legal_actions": legal, "action": key,
                                  "latency_ms": latency}))
    except Exception as exc:
        # Do not persist arbitrary exception text, policy payloads or credentials.
        code = str(exc) if isinstance(exc, EvaluationFailure) else f"{stage}_error"
        send.send(("failure", {"code": code, "stage": stage}))
    finally:
        send.close()


def run_tournament(config, spec, seed, scenario, split="tuning", repeat=0):
    """Run a trusted, importable adapter in its own spawned table process."""
    if scenario not in SCENARIOS or split not in {"tuning", "held_out"}:
        raise ValueError("Choose a supported scenario and tuning or held_out split")
    if type(seed) is not int or not 0 <= seed <= 2**31 - 1:
        raise ValueError("Seed must be an integer between 0 and 2147483647")
    if type(repeat) is not int or repeat < 0:
        raise ValueError("Repeat index must be a nonnegative integer")
    table_id = f"eval-{split}-{seed}-{repeat}-{spec.name}-{scenario}"
    result = {"table_id": table_id, "policy": asdict(spec), "seed": seed,
              "split": split, "repeat": repeat, "scenario": scenario,
              "hero_seat": 0, "status": "failed", "hands": 0, "actions": 0,
              "state_version": None, "chip_total": None,
              "expected_chip_total": config.stack_bb * 10 * 6,
              "chip_conservation": None, "finishing_position": None,
              "prize_units": None, "failure": None, "action_records": []}
    ctx = mp.get_context("spawn")
    receive, send = ctx.Pipe(duplex=False)
    process = ctx.Process(target=_worker, args=(send, config, spec, seed, scenario, table_id))
    start = time.perf_counter()
    try:
        process.start()
        send.close()
        result["worker_pid"] = process.pid
        deadline = time.monotonic() + config.timeout_seconds
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                result["failure"] = {"code": "timeout", "stage": "worker"}
                break
            if not receive.poll(min(0.05, remaining)):
                if not process.is_alive():
                    result["failure"] = {"code": "worker_exit", "stage": "worker"}
                    break
                continue
            try:
                kind, payload = receive.recv()
            except EOFError:
                result["failure"] = {"code": "worker_exit", "stage": "worker"}
                break
            if kind == "action":
                result["action_records"].append(payload)
            elif kind == "progress":
                result.update(payload)
                if payload["chip_total"] != payload["expected_chip_total"]:
                    result["chip_conservation"] = False
                elif result["chip_conservation"] is None:
                    result["chip_conservation"] = True
            elif kind == "complete":
                result.update(payload, status="completed")
                break
            elif kind == "failure":
                result["failure"] = payload
                break
    finally:
        receive.close()
        send.close()
        if process.pid is not None:
            process.join(0.2)
            if process.is_alive():
                process.terminate()
                process.join(1)
            if process.is_alive():
                process.kill()
                process.join(1)
    result["duration_ms"] = (time.perf_counter() - start) * 1000
    # Actions received just before a crash/timeout still count as committed actions.
    result["actions"] = len(result["action_records"])
    hero_times = [a["latency_ms"] for a in result["action_records"] if a["player"] == 0]
    result["hero_decisions"] = len(hero_times)
    result["hero_latency_ms"] = {"total": sum(hero_times),
                                 "mean": sum(hero_times) / len(hero_times) if hero_times else None,
                                 "max": max(hero_times) if hero_times else None}
    deterministic = {k: result[k] for k in ("policy", "seed", "scenario", "status", "hands",
                     "actions", "chip_total", "finishing_position", "prize_units", "failure")}
    deterministic["actions_log"] = [{k: v for k, v in a.items() if k != "latency_ms"}
                                    for a in result["action_records"]]
    result["outcome_sha256"] = hashlib.sha256(json.dumps(deterministic, sort_keys=True).encode()).hexdigest()
    return result


def summarize(results):
    groups = []
    keys = sorted({(r["split"], r["policy"]["name"], r["scenario"]) for r in results})
    for split, policy, scenario in keys:
        rows = [r for r in results if (r["split"], r["policy"]["name"], r["scenario"]) == (split, policy, scenario)]
        completed = [r for r in rows if r["status"] == "completed"]
        groups.append({"split": split, "policy": policy, "scenario": scenario,
                       "attempted": len(rows), "completed": len(completed),
                       "failed": len(rows) - len(completed),
                       "unique_seeds": len({r["seed"] for r in rows}),
                       "completed_unique_seeds": len({r["seed"] for r in completed}),
                       "mean_prize_units": sum(r["prize_units"] for r in completed) / len(completed) if completed else None,
                       "mean_finishing_position": sum(r["finishing_position"] for r in completed) / len(completed) if completed else None})
    return groups


def evaluate(config: EvaluationConfig):
    results = [run_tournament(config, spec, seed, scenario, split, repeat)
               for split, seeds in (("tuning", config.tuning_seeds), ("held_out", config.held_out_seeds))
               for seed in seeds for repeat in range(config.repeats)
               for spec in config.policies for scenario in config.scenarios]
    root = Path(__file__).resolve().parents[1]
    sources = [root / "game.py", root / "agent.py", *sorted((root / "evaluation").glob("*.py"))]
    return {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
            "config": asdict(config),
            "runtime": {"python": platform.python_version(), "pokerkit": version("pokerkit"),
                        "source_sha256": {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}},
            "results": results, "summary": summarize(results)}


def save_report(report, directory):
    """Refuse to overwrite a prior experiment."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "results.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    lines = ["Local tournament evaluation", "", "Prize units are tournament awards, not cash profit or monetary ROI.",
             "Repeated seeds are reproducibility checks, not independent samples.",
             "Means include completed tournaments only; inspect failures before comparing policies.", ""]
    for row in report["summary"]:
        prize = row["mean_prize_units"]
        estimate = f"mean prize units {prize:.2f}" if prize is not None else "no prize estimate"
        lines.append(
            f'{row["split"]} | {row["policy"]} | {row["scenario"]}: '
            f'{row["completed"]}/{row["attempted"]} completed, {row["failed"]} failed, '
            f'{row["completed_unique_seeds"]} completed unique seeds; {estimate}'
        )
    failures = [r for r in report["results"] if r["failure"]]
    lines.extend(f'{r["table_id"]}: {r["failure"]["code"]}' for r in failures)
    lines.extend(["", "Small samples and scripted opponents do not establish strategy strength or unexploitable play."])
    summary = "\n".join(lines) + "\n"
    (directory / "summary.txt").write_text(summary)
    return summary
