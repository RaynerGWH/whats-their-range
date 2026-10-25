import asyncio
import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from wtr.llmbench import Manifest, evaluate, expand
from wtr.llmbench.__main__ import main
from wtr.llmbench.runner import run_game, summarize
from wtr.players import prompt_hash

ROOT = Path(__file__).resolve().parents[3]


def manifest():
    value = json.loads((ROOT / "benchmarks/llm-smoke.json").read_text())
    value.update(seeds=value["seeds"][:1], rotations=[0])
    return value


def test_manifest_presets_rotation_and_offline_validation(tmp_path, monkeypatch):
    value = manifest()
    value["rotations"] = [0, 2, 5]
    runs = expand(value)
    assert len(runs) == 9
    for run in runs:
        cfg = run["config"]
        assert cfg["hero_seat"] == run["rotation"]
        assert all(
            s["instruction_profile"] == "free_play" and s["harness"] == "baseline"
            for s in cfg["seat_configs"]
        )
        assert {s["temperature"] for s in cfg["seat_configs"]} == {1.0}
        assert {v["prompt_sha256"] for v in run["player_versions"]} == {
            prompt_hash(run["preset"] != "chat_disabled")
        }
        for seat in cfg["seat_configs"]:
            assert seat["model"] == (
                "mock/variant"
                if run["preset"] == "model_swap" and seat["seat"] == cfg["hero_seat"]
                else "mock/control"
            )
    for mutation in (
        lambda m: m["table"].update(hero_control="human"),
        lambda m: m.update(rotations=[0, 0]),
        lambda m: m.update(rotations=[6]),
        lambda m: m["seeds"].append({**m["seeds"][0], "split": "held_out"}),
        lambda m: m.update(swap_model="mock/control"),
        lambda m: m["table"]["seat_configs"][0].update(harness="future"),
    ):
        bad = manifest()
        mutation(bad)
        with pytest.raises(ValidationError):
            Manifest.model_validate(bad)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    path, output = tmp_path / "manifest.json", tmp_path / "dry.json"
    path.write_text(json.dumps(value))
    assert main([str(path), "--dry-run", "--output", str(output)]) == 0
    assert json.loads(output.read_text())["provider_calls"] == 0


def test_spawned_mock_runner_reproducibility_outcomes_and_failures(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    one = evaluate(manifest())
    two = evaluate(manifest())
    assert one["mocked"] and len(one["results"]) == 3
    assert [r["outcome_sha256"] for r in one["results"]] == [
        r["outcome_sha256"] for r in two["results"]
    ]
    for result in one["results"]:
        assert result["status"] == "completed" and result["completed"]
        assert sum(p["prize"] for p in result["outcomes"]) == 100
        # Equal starting stacks can produce tied elimination places.
        assert sum(p["place"] == 1 for p in result["outcomes"]) == 1
        assert all(1 <= p["place"] <= 6 for p in result["outcomes"])
        assert sum(p["stack"] for p in result["outcomes"]) == 600
        assert result["rejected_actions"] == 0
        assert result["usage"]["total"]["attempts"] == result["actions"]
        assert result["usage"]["total"]["fallbacks"] == 0
        assert bool(result["chat"]) == (result["preset"] != "chat_disabled")
    assert all(s["approximate_95pct_normal_interval"] is None for s in one["summary"])
    bad = manifest()
    bad["presets"] = ["same_model"]
    bad["table"]["llm_limits"] = {"max_calls_total": 0}
    exhausted = evaluate(bad)["results"][0]
    assert exhausted["status"] == "budget_exhausted" and not exhausted["completed"]
    assert exhausted["outcomes"] is None and exhausted["provisional_outcomes"]
    assert exhausted["usage"]["total"]["attempts"] == 0
    assert exhausted["usage"]["total"]["fallbacks"] == 1
    summary = summarize([exhausted])[0]
    assert summary["statuses"] == {"budget_exhausted": 1}
    assert summary["hero_prize_mean_complete_provider_only"] is None


@pytest.mark.parametrize("failure", ["http", "invalid", "timeout", "missing_usage"])
def test_failure_injection_records_attempts_actual_or_missing_usage(failure):
    value = manifest()
    value["presets"] = ["same_model"]
    value["table"]["llm_limits"] = {"deadline_seconds": 0.05}
    result = evaluate(value, failure=failure)["results"][0]
    assert result["status"] == (
        "completed" if failure == "missing_usage" else "completed_with_fallbacks"
    )
    assert result["usage"]["total"]["attempts"] == result["actions"]
    assert result["usage"]["total"]["fallbacks"] == (
        0 if failure == "missing_usage" else 1
    )
    assert result["usage"]["total"]["input_tokens"] == (
        result["actions"] * 10 if failure == "invalid" else None
    )
    if failure != "missing_usage":
        assert result["accepted_actions"][0]["source"] == "heuristic"
        assert all(
            c["state_version"] != result["accepted_actions"][0]["state_version"]
            for c in result["chat"]
        )


@pytest.mark.parametrize(
    "rule,expected",
    [
        ("max_actions", "action_limit"),
        ("max_hands", "hand_limit"),
        ("timeout_seconds", "timeout"),
    ],
)
def test_stopping_limits_and_manual_rejection(rule, expected):
    value = manifest()
    value["presets"] = ["same_model"]
    value["stopping"][rule] = 0.1 if rule == "timeout_seconds" else 1
    if rule == "max_hands":
        value["table"]["stack_bb"] = 200
    run = expand(value)[0]
    result = asyncio.run(
        run_game(run, failure="timeout" if rule == "timeout_seconds" else None)
    )
    assert (
        result["status"] == expected
        and not result["completed"]
        and result["outcomes"] is None
    )
    assert result["usage"]["total"]["attempts"] >= 1
    run["config"]["hero_control"] = "human"
    with pytest.raises(ValueError, match="Human or mixed"):
        asyncio.run(run_game(run))


def test_uncertainty_clusters_rotations_by_seed():
    rows = []
    for seed, prizes in ((1, [0, 100]), (2, [20, 40])):
        for rotation, prize in enumerate(prizes):
            rows.append(
                {
                    "preset": "same_model",
                    "split": "held_out",
                    "seed_set": {"deck": seed, "policy": seed + 100},
                    "status": "completed",
                    "config": {"hero_seat": 0},
                    "outcomes": [{"prize": prize}],
                }
            )
    result = summarize(rows)[0]
    assert result["runs"] == 4 and result["independent_seed_sets"] == 2
    assert result["hero_prize_mean_complete_provider_only"] == 40
    assert result["approximate_95pct_normal_interval"] == pytest.approx([20.4, 59.6])


def crashed_worker(send, run, mock, failure):
    import os

    os._exit(2)


def blocked_worker(send, run, mock, failure):
    import time

    from wtr.llmbench.runner import initial_result

    checkpoint = initial_result(run)
    checkpoint["usage"]["total"]["attempts"] = 1
    send.send(("progress", checkpoint))
    time.sleep(30)


@pytest.mark.parametrize(
    "target,expected", [(crashed_worker, "worker_error"), (blocked_worker, "timeout")]
)
def test_parent_preserves_incomplete_runs_and_hard_deadline(
    monkeypatch, target, expected
):
    from wtr.llmbench import runner

    value = manifest()
    value["stopping"]["timeout_seconds"] = 0.1
    run = expand(value)[0]
    monkeypatch.setattr(runner, "_child", target)
    result = runner.isolated_run(run)
    assert result["status"] == expected
    assert not result["completed"] and result["outcomes"] is None
    assert (
        not result["usage_complete"] and result["error"]["code"] == "WorkerIncomplete"
    )
    assert result["usage"]["total"]["attempts"] == (1 if expected == "timeout" else 0)
