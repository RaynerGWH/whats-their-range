"""Real native execution unless a test explicitly marks the subprocess mocked."""

import asyncio
from copy import deepcopy
from dataclasses import replace
import json
import subprocess

import httpx
import pytest

from wtr.agent import Agent
from wtr.evaluation import EvaluationConfig, POLICIES, run_tournament
from wtr.game import Tournament
from wtr.models import TournamentConfig
from wtr.opponents import (
    OpponentError,
    Opponents,
    PublicStats,
    card_number,
    normalize,
    parse_decision,
    require_native,
    resolve_seeds,
    situation,
)


def config(**changes):
    return TournamentConfig(
        opponents="pokerth",
        opponent_seed=43,
        personality_seed=44,
        hero_seed=42,
        stack_bb=10,
        hands_per_level=2,
        **changes,
    ).model_dump()


def test_real_native_complete_reproducible_tournaments():
    require_native()  # Build is required, never silently skip the native acceptance tests.
    cfg = EvaluationConfig(opponents="pokerth")
    for deck, policy in ((1, 43), (7, 91)):
        cfg = replace(cfg, opponent_seed=policy)
        first = run_tournament(cfg, POLICIES["heuristic"], deck, "standard")
        second = run_tournament(cfg, POLICIES["heuristic"], deck, "standard")
        assert first["status"] == second["status"] == "completed", first["failure"]
        assert first["outcome_sha256"] == second["outcome_sha256"]
        assert first["chip_conservation"] and first["chip_total"] == 600
        assert first["hero_decisions"] > 0
        assert all(a["action"] in a["legal_actions"] for a in first["action_records"])
        assert all(
            p["stack"] >= 0 for a in first["action_records"] for p in a["players"]
        )


def test_native_on_every_street_and_player_count():
    seen = set()
    for count in range(2, 7):
        g = Tournament("opaque", config())
        # PokerKit legal observations, all six identities can occur in shrinking tables.
        g.hand = 0
        g.button = 5
        g.stacks = [0] + [500] * (count - 1) + [0] * (6 - count)
        # Include seat 5 so there are count players, all native policy seats where possible.
        g.stacks[0] = 500
        g.total = 500 * count
        g.new_hand()
        opponents = Opponents(config())
        for _ in range(150):
            if g.phase == "hand_complete" or g.status == "finished":
                break
            obs = g.observation()
            if obs["player"] != 0:
                key = opponents.decide(
                    obs
                )  # Real native call, regardless of execution below.
                assert key in [a["key"] for a in obs["legal"]]
                seen.add((count, obs["street"]))
            # Passive legal execution deliberately reaches every street.
            key = next(a["key"] for a in obs["legal"] if a["kind"] == "call")
            g.apply(key, obs["version"])
            opponents.observe(obs, key)
    assert seen == {
        (n, s) for n in range(2, 7) for s in ("preflop", "flop", "turn", "river")
    }


def restricted_game():
    g = Tournament("opaque", config())
    g.hand, g.button = 0, 3
    g.stacks, g.total = [0, 100, 25, 100, 0, 0], 225
    g.new_hand()
    return g


def test_short_allin_does_not_reopen_and_side_pots_settle():
    g = restricted_game()
    assert g.actor == 3
    g.apply("raise:20", g.version)
    g.apply("call", g.version)
    assert g.actor == 2
    obs = g.observation()
    assert normalize(obs, (5, 0, 10000)) == "raise:25"
    g.apply("raise:25", g.version)
    opponents = Opponents(config())
    obs = g.observation()
    assert not any(a["kind"] == "raise" for a in obs["legal"])
    assert normalize(obs, (6, 0, 0)) == "call"
    assert opponents.decide(obs) in {"fold", "call"}
    g.apply("call", g.version)
    g.apply("call", g.version)
    # Two larger stacks can now bet into a side pot while the short stack is all-in.
    obs = g.observation()
    assert obs["street"] == "flop"
    g.apply(
        max(
            (a for a in obs["legal"] if a["kind"] == "raise"), key=lambda a: a["amount"]
        )["key"],
        g.version,
    )
    obs = g.observation()
    assert opponents.decide(obs) in [a["key"] for a in obs["legal"]]
    g.apply("call", g.version)
    assert g.phase in ("hand_complete", "complete")
    assert sum(g.stacks) == 225 and min(g.stacks) >= 0


def test_increment_conversion_clamping_and_safe_passive_mapping():
    g = restricted_game()
    obs = g.observation()
    assert normalize(obs, (5, 0, 10)) == "raise:20"  # highest 10 + increment 10
    assert normalize(obs, (5, 0, 999999)) == "raise:100"
    assert normalize(obs, (2, 0, 0)) == "call"  # cannot check facing a bet
    g.apply("call", g.version)
    g.apply("call", g.version)
    obs = g.observation()  # Big blind can check.
    assert normalize(obs, (1, 0, 0)) == "check"
    assert normalize(obs, (3, 0, 0)) == "check"
    assert card_number("2c") == 0 and card_number("As") == 51


@pytest.mark.parametrize(
    "output",
    [
        "",
        "0 0 0",
        "7 0 0",
        "5 -1 10",
        "5 0 nan",
        "5 0 10 extra",
        "x" * 101,
        "5 0 999999999999",
        "٥ 0 1",
    ],
)
def test_malformed_response_rejected(output):
    with pytest.raises(OpponentError, match="invalid decision"):
        parse_decision(output)


def test_missing_build_and_native_failure_are_explicit(tmp_path, monkeypatch):
    monkeypatch.setenv("POKERTH_BINARY", str(tmp_path / "missing"))
    with pytest.raises(OpponentError, match="build_pokerth.py"):
        Opponents(config())
    # Explicit legacy remains available without a native build.
    Opponents({**config(), "opponents": "legacy"})
    monkeypatch.delenv("POKERTH_BINARY")
    opponents = Opponents(config())
    obs = Tournament("opaque", config()).observation()

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("native", 2)

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(OpponentError, match="timed out"):
        opponents.decide(obs)


def test_native_rejects_bounded_malformed_input():
    binary = require_native()
    for request in ("x\n", "1 " * 600 + "\n", "1 9 0 1\n"):
        result = subprocess.run(
            [str(binary)], input=request, text=True, capture_output=True, timeout=2
        )
        assert result.returncode == 2
        assert result.stdout == ""
        assert result.stderr == "PokerTH bridge rejected input or decision\n"


def test_public_statistics_opportunities_and_reset():
    stats = PublicStats()
    obs = {"player": 1, "hand": 1, "street": "preflop"}
    stats.observe(obs, "call")
    stats.observe(obs, "raise:40")
    assert stats.players[1].preflop_opportunities == stats.players[1].vpip == 1
    for hand in range(2, 11):
        stats.observe({**obs, "hand": hand}, "fold")
    assert stats.percentages([1]) == (10, -1)
    for i in range(10):
        stats.observe({**obs, "street": "flop"}, "raise:40" if i < 3 else "check")
    assert stats.percentages([1]) == (10, 30)
    assert PublicStats().percentages([1]) == (-1, -1)


def test_rng_assignment_memory_and_information_boundaries(monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("OPENROUTER_API_KEY", "mock-only")
    g = Tournament("opaque", config())
    opponents = Opponents(config())
    before = g.rng.getstate()
    obs = g.observation()
    opponents.decide(obs)
    assert g.rng.getstate() == before
    assert len({r.getstate() for r in opponents.random.values()}) == 5
    other = Opponents({**config(), "personality_seed": 100})
    assert opponents.personalities != other.personalities
    assert g.observation() == obs  # No identity changes from hidden assignments.
    opponents.observe(obs, "call")
    assert other.stats.players[obs["player"]].preflop_opportunities == 0
    clean = situation(obs, PublicStats())
    dirty = deepcopy(obs)
    dirty.update(opponent_seed=1234, personality_seed=99, source="private-source")
    for p in dirty["players"]:
        p.update(cards=["As", "Ad"], profile="private-marker")
    assert situation(dirty, PublicStats()) == clean
    sent = []

    def handler(request):
        payload = json.loads(request.content)
        sent.append(payload)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "action": "call",
                                    "summary": "Mock",
                                    "uncertainty": "Test",
                                    "evidence_ids": [],
                                }
                            )
                        }
                    }
                ]
            },
        )

    for observation in (obs, dirty):
        agent = Agent("openrouter", "test/mock", transport=httpx.MockTransport(handler))
        asyncio.run(agent.decide(observation))
        assert "private-marker" not in json.dumps(agent.last_trace)
        agent.close()
    assert sent[0] == sent[1]
    seeds = resolve_seeds(config())
    assert seeds["opponent_seed"] == 43
    a, b = resolve_seeds({}), resolve_seeds({})
    assert a != b and a["opponent_seed"] != a["personality_seed"]
