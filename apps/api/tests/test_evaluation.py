import asyncio
from dataclasses import replace
import json
import multiprocessing as mp
import os
import time

import pytest

from wtr.agent import Agent
from wtr.game import Tournament
from wtr.models import TournamentConfig
from wtr.evaluation import EvaluationConfig, POLICIES, PolicySpec, evaluate, run_tournament, save_report
from wtr.evaluation.policies import Heuristic, Shove, opponent_action
from wtr.evaluation.__main__ import main


class PrivatePolicy(Shove):
    def decide(self, obs):
        assert set(obs) == {"table_id", "hand", "version", "player", "position", "hole", "board",
                            "street", "pot", "to_call", "big_blind", "players", "hand_start_stacks",
                            "payouts", "history", "legal", "opponents"}
        assert obs["player"] == 0 and len(obs["hole"]) == 2
        assert all(set(p) == {"seat", "stack", "bet", "active", "position"} for p in obs["players"])
        assert all(set(p) == {"seat", "name", "actions", "raises", "folds", "calls", "recent_actions"}
                   for p in obs["opponents"])
        decision = super().decide(obs)
        obs["legal"].clear()
        obs["hole"].clear()
        obs["version"] = -100
        return decision


class InvalidPolicy(Shove):
    def decide(self, obs):
        obs["legal"].append({"key": "raise:999999999"})
        return {"action": "raise:999999999", "state_version": obs["version"]}


class StalePolicy(Shove):
    def decide(self, obs):
        return {"action": obs["legal"][0]["key"], "state_version": obs["version"] - 1}


class MalformedPolicy(Shove):
    def decide(self, obs):
        return "call"


class BrokenPolicy(Shove):
    def decide(self, obs):
        raise ValueError("SECRET: provider response or hidden data")


class StalledPolicy(Shove):
    def decide(self, obs):
        time.sleep(30)
        return super().decide(obs)


class AsyncPolicy(Shove):
    async def decide(self, obs):
        return super().decide(obs)


def spec(cls):
    return PolicySpec(cls.__name__, "test-v1", f"test_evaluation:{cls.__name__}")


def config(**kwargs):
    return EvaluationConfig(tuning_seeds=(1,), held_out_seeds=(101,),
                            policies=(POLICIES["shove"],), scenarios=("repeated-shove",), **kwargs)


def test_reproducible_complete_tournaments_and_saved_results(tmp_path):
    report = evaluate(config(repeats=2))
    rows = report["results"]
    assert len(rows) == 4 and all(r["status"] == "completed" for r in rows)
    assert all(r["chip_conservation"] and r["chip_total"] == 600 for r in rows)
    assert all(sum(r["prizes"]) == 100 and 1 <= r["finishing_position"] <= 6 for r in rows)
    assert all(r["duration_ms"] > 0 and r["hero_latency_ms"]["mean"] >= 0 for r in rows)
    assert all(r["worker_pid"] != os.getpid() for r in rows)
    for left, right in ((rows[0], rows[1]), (rows[2], rows[3])):
        assert left["outcome_sha256"] == right["outcome_sha256"]
    assert all(s["attempted"] == 2 and s["unique_seeds"] == 1 for s in report["summary"])
    for row in rows:
        assert row["actions"] == len(row["action_records"])
        versions = [a["state_version"] for a in row["action_records"]]
        assert versions == sorted(set(versions))
        assert all(a["action"] in a["legal_actions"] for a in row["action_records"])
    summary = save_report(report, tmp_path / "experiment")
    stored = json.loads((tmp_path / "experiment/results.json").read_text())
    assert stored["results"] == rows
    assert "not cash profit" in summary and "not independent samples" in summary
    assert "hole" not in json.dumps(stored) and "deck_cards" not in json.dumps(stored)
    with pytest.raises(FileExistsError):
        save_report(report, tmp_path / "experiment")


@pytest.mark.parametrize("cls", [PrivatePolicy, AsyncPolicy])
def test_permitted_policy_boundary_and_async_adapter(cls):
    result = run_tournament(config(), spec(cls), 1, "repeated-shove")
    assert result["status"] == "completed", result["failure"]
    assert result["hero_decisions"] > 0


@pytest.mark.parametrize("cls,code", [(InvalidPolicy, "illegal_policy_action"),
                                      (StalePolicy, "stale_policy_response"),
                                      (MalformedPolicy, "invalid_policy_response"),
                                      (BrokenPolicy, "policy_decision_error")])
def test_invalid_policies_are_failures_without_executing_action(cls, code):
    result = run_tournament(config(), spec(cls), 1, "repeated-shove")
    assert result["status"] == "failed" and result["failure"]["code"] == code
    assert result["hero_decisions"] == 0 and result["prize_units"] is None
    assert "SECRET" not in json.dumps(result)


def test_invalid_factory_is_reported():
    result = run_tournament(config(), PolicySpec("bad", "1", "wtr.evaluation.policies:Missing"), 1, "standard")
    assert result["failure"]["code"] == "policy_initialization_error"
    assert result["chip_conservation"] is None


def test_stalled_policy_is_terminated_and_following_table_completes():
    result = run_tournament(config(timeout_seconds=2), spec(StalledPolicy), 1, "repeated-shove")
    assert result["failure"]["code"] == "timeout" and result["duration_ms"] < 6000
    assert result["worker_pid"] not in {p.pid for p in mp.active_children()}
    assert run_tournament(config(), POLICIES["shove"], 1, "repeated-shove")["status"] == "completed"


@pytest.mark.parametrize("limits,code", [({"max_actions": 1}, "action_limit"), ({"max_hands": 1}, "hand_limit")])
def test_execution_limits(limits, code):
    result = run_tournament(config(**limits), POLICIES["check-call"], 1, "standard")
    assert result["failure"]["code"] == code and result["prize_units"] is None


@pytest.mark.parametrize("change", [dict(held_out_seeds=(1,)), dict(tuning_seeds=(1, 1)),
                                   dict(repeats=0), dict(timeout_seconds=float("nan")),
                                   dict(max_actions=0), dict(scenarios=("bad",)),
                                   dict(opponent_profiles=("unknown",) * 5),
                                   dict(policies=(POLICIES["shove"],) * 2)])
def test_invalid_experiment_configuration(change):
    with pytest.raises(ValueError):
        replace(config(), **change)


def test_heuristic_matches_existing_agent_without_model_calls(monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    game = Tournament("test", TournamentConfig(stack_bb=10, hands_per_level=2).model_dump())
    agent, policy = Agent(seed=42), Heuristic(42)
    for _ in range(3):
        obs = game.observation()
        expected = asyncio.run(agent.decide(obs))
        actual = policy.decide(obs)
        assert actual["action"] == expected["action"]
        game.apply(actual["action"], obs["version"])
        game.version += 1
        if game.phase == "hand_complete":
            game.new_hand()
    assert agent.calls == 0


def test_pressure_adapter_uses_maximum_legal_raise():
    game = Tournament("test", TournamentConfig().model_dump())
    obs = game.observation()
    expected = max((a for a in obs["legal"] if a["kind"] == "raise"), key=lambda a: a["amount"])
    assert opponent_action(obs, "repeated-shove", "tight", game.rng) == expected["key"]
    passive = {**obs, "legal": [a for a in obs["legal"] if a["kind"] != "raise"]}
    assert Shove(0).decide(passive)["action"] == "call"


def test_failed_results_do_not_become_zero_prize_estimates(tmp_path):
    report = evaluate(replace(config(), policies=(spec(InvalidPolicy),)))
    assert all(s["mean_prize_units"] is None and s["failed"] == 1 for s in report["summary"])
    assert "no prize estimate" in save_report(report, tmp_path / "failures")


def test_cli_saves_results_and_returns_failure_exit_code(tmp_path):
    output = tmp_path / "cli"
    code = main(["--policy", "check-call", "--scenario", "repeated-shove",
                 "--held-out-seeds", "", "--max-actions", "1", "--output", str(output)])
    assert code == 1 and (output / "results.json").exists()
    with pytest.raises(SystemExit) as exc:
        main(["--adapter", "missing:policy"])
    assert exc.value.code == 2


def test_single_shover_only_replaces_designated_seat():
    import random
    from wtr.agent import assess, baseline

    game = Tournament("test", TournamentConfig().model_dump())
    obs = game.observation()
    assert obs["player"] != 1
    expected = baseline(obs, assess({"observation": obs})["metrics"], random.Random(9), "tight")
    assert opponent_action(obs, "single-shover", "tight", random.Random(9)) == expected
    designated = {**obs, "player": 1}
    assert opponent_action(designated, "single-shover", "tight", random.Random(9)) == Shove(0).decide(designated)["action"]


def test_winner_take_all_and_check_call_baseline():
    result = run_tournament(config(payouts="winner-take-all"), POLICIES["check-call"], 1, "repeated-shove")
    assert result["status"] == "completed"
    assert sorted(result["prizes"]) == [0, 0, 0, 0, 0, 100]
    assert all(a["action"] in {"check", "call"} for a in result["action_records"] if a["player"] == 0)


def test_direct_runner_rejects_unknown_scenario():
    with pytest.raises(ValueError, match="supported scenario"):
        run_tournament(config(), POLICIES["shove"], 1, "typo")
