"""Semantic boundary regressions: field allowlists alone cannot catch leaks."""

import asyncio
from copy import deepcopy
import json
from unittest.mock import Mock
from uuid import UUID

import httpx

from wtr.agent import Agent, assess
from wtr.evaluation import EvaluationConfig, PolicySpec, run_tournament
from wtr.evaluation.policies import Shove
from wtr.game import Tournament
from wtr.models import TournamentConfig
from wtr.strategy import analyze
from wtr.tracing import LangSmithExporter, private_observation


class BlindedPolicy(Shove):
    def __init__(self, seed):
        # Fixed policy RNG input is independent of either hidden deck seed.
        assert seed == 42

    def decide(self, obs):
        assert len(obs["table_id"]) == 32
        UUID(obs["table_id"])
        assert all(p["name"] == f"Player {p['seat'] + 1}" for p in obs["opponents"])
        for event in obs["history"]:
            assert event["id"].startswith("e") and event["id"][1:].isdigit()
        assert "repeated-shove" not in json.dumps(obs)
        assert "held_out" not in json.dumps(obs)
        return super().decide(obs)


def test_evaluation_is_blinded_at_factory_and_observation_boundary():
    config = EvaluationConfig()
    spec = PolicySpec(
        "sensitive-policy-label", "test", "test_stage1_privacy:BlindedPolicy"
    )
    first = run_tournament(config, spec, 101, "repeated-shove", "held_out")
    second = run_tournament(config, spec, 101, "repeated-shove", "held_out", repeat=1)
    third = run_tournament(config, spec, 102, "repeated-shove", "held_out")
    assert all(r["status"] == "completed" for r in (first, second, third))
    assert first["protocol_version"] == 3
    assert first["table_id"] != second["table_id"]
    assert first["outcome_sha256"] == second["outcome_sha256"]
    assert first["seed"] == 101 and first["scenario"] == "repeated-shove"


def public_state():
    game = Tournament("a" * 32, TournamentConfig().model_dump())
    for _ in range(3):
        obs = game.observation()
        action = next(a["key"] for a in obs["legal"] if a["kind"] == "call")
        game.apply(action, obs["version"])
        game.version += 1
    return game


def test_spectator_changes_do_not_affect_observation(monkeypatch):
    from wtr import game as module

    game = public_state()
    expected = game.observation()
    actor = game.actor
    game.config.update(seed=987654, name="hidden-scenario")
    game.state.deck_cards.reverse()
    for seat in game.holes:
        if seat != actor:
            game.holes[seat] = ["2c", "3c"]
    monkeypatch.setattr(module, "NAMES", ("hidden-alias",) * 6)
    monkeypatch.setattr(module, "PROFILES", ("hidden-profile",) * 6)
    for event in game.history:
        event["text"] = "hidden-seed-scenario-provider-key"
        event["id"] = "eval-held_out-987654-repeated-shove:" + event["id"]
        event["profile"] = "hidden-profile"
    assert game.observation() == expected
    assert expected["history"]  # Meaningful public actions/evidence are retained.


def test_forbidden_metadata_cannot_change_payload_tools_or_export(monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("OPENROUTER_API_KEY", "mock-only")
    observation = public_state().observation()
    dirty = deepcopy(observation)
    dirty.update(seed=101, scenario="hidden-marker", snapshot={"deck": "hidden-marker"})
    for p in dirty["players"]:
        p.update(cards=["hidden-marker"], profile="hidden-marker")
    for p in dirty["opponents"]:
        p.update(name="hidden-marker", archetype="hidden-marker")
    for event in dirty["history"] + [
        e for p in dirty["opponents"] for e in p["recent_actions"]
    ]:
        event.update(text="hidden-marker", seed=101)
        event["id"] = "hidden-marker:" + event["id"]
    permitted = private_observation(dirty)
    assert permitted == observation
    metrics = assess({"observation": observation})["metrics"]
    assert analyze(permitted, {**metrics, "raw": "hidden-marker"}) == analyze(
        observation, metrics
    )
    sent, records = [], []

    def handler(request):
        payload = json.loads(request.content)
        sent.append(payload)
        obs = json.loads(payload["messages"][1]["content"])["observation"]
        evidence = [e["id"] for e in obs["history"]][-1:]
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "action": next(
                                        a["key"]
                                        for a in obs["legal"]
                                        if a["kind"] == "call"
                                    ),
                                    "summary": "Mock decision",
                                    "uncertainty": "Test only",
                                    "evidence_ids": evidence,
                                }
                            )
                        }
                    }
                ]
            },
        )

    for obs in (observation, dirty):
        agent = Agent("openrouter", "test/mock", transport=httpx.MockTransport(handler))
        decision = asyncio.run(agent.decide(obs))
        assert decision["source"] == "openrouter" and decision["evidence_ids"]
        records.append(agent.last_trace)
    assert sent[0] == sent[1]
    for first, second in zip(records[0]["spans"], records[1]["spans"]):
        assert first["inputs"] == second["inputs"]
        assert first["outputs"] == second["outputs"]
    client = Mock()
    client._get_langsmith_api_sync.return_value.runs.get_url.return_value.url = (
        "https://smith.langchain.com/test"
    )
    exporter = LangSmithExporter(client_factory=lambda: client)
    exporter.submit(records[1])
    exporter.queue.join()
    exporter.close()
    assert "hidden-marker" not in json.dumps(records)
    assert "hidden-marker" not in repr(client.create_run.call_args_list)


def test_review_pack_regenerates_from_legal_play():
    import importlib.util
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location(
        "review_pack", root / "scripts/stage1_review_pack.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    generated = module.build_pack()
    assert generated == json.loads(
        (root / "docs/review/stage-1-hands.json").read_text()
    )
    assert (
        module.render_markdown(generated)
        == (root / "docs/review/stage-1-hands.md").read_text()
    )
    assert len(generated["cases"]) == 9
    assert any(
        c["intent"] == "semi_bluff"
        for case in generated["cases"]
        for c in case["candidate_hypotheses"]
    )
    for case in generated["cases"]:
        assert private_observation(case["observation"]) == case["observation"]
