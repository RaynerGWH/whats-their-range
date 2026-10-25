"""Contract and counterexample tests for conditional candidate analysis."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import random

import pytest

from wtr.agent import assess
from wtr.game import Tournament
from wtr.models import TournamentConfig
from wtr.strategy import analyze


def observation(hole=("8c", "6d"), board=("As", "Kd", "7h", "2c", "3s")):
    return {
        "table_id": "strategy-test", "hand": 3, "version": 12, "player": 0,
        "position": "BTN", "hole": list(hole), "board": list(board),
        "street": {0: "preflop", 3: "flop", 4: "turn", 5: "river"}[len(board)],
        "pot": 100, "to_call": 0, "big_blind": 10,
        "players": [
            {"seat": 0, "stack": 500, "bet": 0, "active": True, "position": "BTN"},
            {"seat": 1, "stack": 500, "bet": 0, "active": True, "position": "BB"},
        ],
        "hand_start_stacks": [550, 550], "payouts": [100], "history": [], "opponents": [],
        "legal": [
            {"key": "check", "kind": "call", "amount": 0},
            {"key": "raise:50", "kind": "raise", "amount": 50},
        ],
    }


def candidate(result, key="raise:50"):
    return next(c for c in result["candidates"] if c["action"] == key)


def event(identifier="e1", action="raise:30"):
    return {"id": identifier, "hand": 3, "street": "river", "player": 1, "action": action}


def test_contract_legality_and_pure_bluff_with_check_alternative():
    obs = observation()
    result = analyze(obs, {})
    assert set(result) == {"schema_version", "state_version", "candidates", "uncertainty"}
    assert result["schema_version"] == 1 and result["state_version"] == 12
    assert [(c["action"], c["intent"]) for c in result["candidates"]] == [
        ("check", "check"), ("raise:50", "bluff")
    ]
    for c in result["candidates"]:
        assert set(c) == {"action", "intent", "rationale", "evidence_ids", "assumptions", "limitations", "estimates", "continuation"}
        assert c["assumptions"] and c["limitations"] and c["continuation"]
    bluff = candidate(result)
    threshold = bluff["estimates"]["zero_equity_fold_rate_required"]
    assert threshold["value"] == pytest.approx(1 / 3)
    assert threshold["unit"] == "fraction of responses"
    assert "not checking or calling" in " ".join(threshold["assumptions"])
    assert "not a predicted response" in " ".join(bluff["limitations"])
    json.dumps(result, allow_nan=False)


def test_raise_to_uses_incremental_commitment_not_target_or_raise_increment():
    obs = observation()
    obs["players"][0]["bet"] = 20
    obs["players"][1]["bet"] = 30
    obs["to_call"] = 10
    obs["legal"] = [
        {"key": "fold", "kind": "fold", "amount": 0},
        {"key": "call", "kind": "call", "amount": 10},
        {"key": "raise:50", "kind": "raise", "amount": 50},
    ]
    result = analyze(obs, {})
    bluff = candidate(result)
    assert bluff["estimates"]["additional_commitment"]["value"] == 30
    assert bluff["estimates"]["zero_equity_fold_rate_required"]["value"] == pytest.approx(30 / 130)
    call = candidate(result, "call")
    assert call["intent"] == "call"
    assert call["estimates"]["checkdown_call_share_required"]["value"] == pytest.approx(10 / 110)
    assert candidate(result, "fold")["intent"] == "fold"


@pytest.mark.parametrize("hole,board,intent", [
    (("As", "Js"), ("Ks", "7s", "2d"), "semi_bluff"),
    (("8c", "9d"), ("7s", "6h", "2d"), "semi_bluff"),
    (("As", "5d"), ("2c", "3h", "Kd"), "semi_bluff"),  # wheel gutshot
    (("8c", "6d"), ("As", "Kd", "7h"), "bluff"),
    (("As", "Qd"), ("Ac", "7s", "2d"), "value"),
    (("Qs", "Qd"), ("Jc", "7s", "2d"), "value"),
    (("7c", "7d"), ("As", "7s", "2d"), "value"),
    (("As", "Js"), ("Ks", "7s", "2s"), "value"),
    (("Qs", "Qd"), (), "value"),
    (("As", "Kd"), (), "value"),
])
def test_intent_uses_visible_hand_features(hole, board, intent):
    assert candidate(analyze(observation(hole, board), {}))["intent"] == intent


@pytest.mark.parametrize("hole,board", [
    (("8c", "6d"), ("As", "Ks", "7s", "2s")),  # board-only flush draw
    (("2c", "3d"), ("6s", "7h", "8d", "9s")),  # board-only straight draw
    (("As", "Js"), ("Ks", "7s", "2d", "3h", "8c")),  # missed river draw
    (("As", "Js"), ("Ks", "7h", "2d")),  # only a backdoor flush
    (("3c", "4d"), ("As", "Ah", "Ac", "Kd", "Ks")),  # board plays
])
def test_no_semibluff_from_board_only_backdoor_or_completed_runout(hole, board):
    assert candidate(analyze(observation(hole, board), {}))["intent"] == "bluff"


def test_unsupported_preflop_classification_is_omitted_not_invented():
    result = analyze(observation(("8c", "6d"), ()), {})
    assert [c["action"] for c in result["candidates"]] == ["check"]
    assert "Raise intents are omitted" in " ".join(result["uncertainty"])


def test_sparse_and_duplicate_evidence_never_establishes_fold_tendency():
    obs = observation()
    empty = analyze(obs, {})
    obs["history"] = [event(action="fold")]
    obs["opponents"] = [{"seat": 1, "folds": 999, "actions": 999, "recent_actions": [event(action="fold")]}]
    result = analyze(obs, {})
    assert "Sparse evidence: 1 distinct" in " ".join(result["uncertainty"])
    assert candidate(result)["evidence_ids"] == []  # no irrelevant fold citation
    assert candidate(result)["estimates"] == candidate(empty)["estimates"]
    assert "do not establish a tendency" in " ".join(result["uncertainty"])


def test_current_hand_history_cites_only_actual_current_street_opponent_raises():
    obs = observation()
    obs["history"] = [event(), {**event("old"), "hand": 2}, {**event("flop"), "street": "flop"},
                      {**event("hero"), "player": 0}, event("check", "check")]
    result = analyze(obs, {})
    assert candidate(result)["evidence_ids"] == ["e1"]
    assert "1 cited opponent raises" in candidate(result)["rationale"]


@pytest.mark.parametrize("condition", ["multiway", "all_in", "overbet", "zero_pot"])
def test_unsupported_fold_thresholds_are_withheld(condition):
    obs = observation()
    if condition == "multiway":
        obs["players"].append({"seat": 2, "stack": 100, "bet": 0, "active": True, "position": "SB"})
    elif condition == "all_in":
        obs["players"][1]["stack"] = 0
    elif condition == "overbet":
        obs["players"][1]["stack"] = 40
    else:
        obs["pot"] = 0
    bluff = candidate(analyze(obs, {}))
    assert "zero_equity_fold_rate_required" not in bluff["estimates"]
    assert "Fold threshold withheld" in " ".join(bluff["limitations"])


def test_multiway_call_does_not_report_full_pot_threshold():
    obs = observation()
    obs["players"].append({"seat": 2, "stack": 50, "bet": 10, "active": True, "position": "SB"})
    obs["legal"] = [{"key": "call", "kind": "call", "amount": 10}]
    obs["to_call"] = 10
    call = candidate(analyze(obs, {}), "call")
    assert "checkdown_call_share_required" not in call["estimates"]


def test_short_stack_and_pairwise_matched_exposure_account_for_existing_bets():
    obs = observation()
    obs["players"][0].update(stack=500, bet=20)
    obs["players"][1].update(stack=80, bet=30)
    result = analyze(obs, {})
    assert "Short effective stack" in " ".join(result["uncertainty"])
    assert candidate(result)["estimates"]["effective_commitment"]["value"] == [{"seat": 1, "chips": 90}]


@pytest.mark.parametrize("equity", [None, float("nan"), float("inf"), -0.1, 1.1, "0.8", True])
def test_invalid_metrics_do_not_create_false_precision(equity):
    result = analyze(observation(), {"equity": equity})
    assert "random_range_equity_reference" not in candidate(result)["estimates"]
    json.dumps(result, allow_nan=False)


def test_random_range_equity_cannot_turn_weak_hand_into_value_claim():
    metrics = {"equity": 0.99, "standard_error": 0.001, "icm_at_hand_start": 90}
    result = analyze(observation(), metrics)
    assert candidate(result)["intent"] == "bluff"
    estimates = candidate(result)["estimates"]
    assert "not the range that continues" in " ".join(estimates["random_range_equity_reference"]["assumptions"])
    assert "not confidence" in " ".join(estimates["sampling_standard_error"]["assumptions"])
    assert "tournament action values are not modeled" in " ".join(result["uncertainty"])


def test_inputs_and_outputs_are_independent_and_parallel_calls_deterministic():
    obs, metrics = observation(), {"equity": 0.2, "standard_error": 0.03}
    before = deepcopy((obs, metrics))
    expected = analyze(obs, metrics)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: analyze(obs, metrics), range(12)))
    assert all(r == expected for r in results)
    assert (obs, metrics) == before
    results[0]["candidates"][0]["estimates"]["effective_commitment"]["value"][0]["chips"] = -1
    results[0]["candidates"][0]["limitations"].append("mutated")
    assert results[1] == analyze(obs, metrics) == expected


def test_unknown_private_and_free_text_fields_are_not_echoed_or_used():
    obs = observation()
    expected = analyze(obs, {})
    obs.update(opponent_cards="SENTINEL", future_deck="SENTINEL", provider_key="SENTINEL")
    for player in obs["players"]:
        player.update(cards=["SENTINEL"], profile="SENTINEL")
    obs["opponents"] = [{"seat": 1, "name": "SENTINEL", "profile": "SENTINEL", "recent_actions": []}]
    obs["history"] = [{"text": "SENTINEL", "player": 1}]
    result = analyze(obs, {"raw_response": "SENTINEL", "assumption": "SENTINEL"})
    assert result == expected
    assert "SENTINEL" not in json.dumps(result)


def test_invalid_cards_and_empty_legal_menu_do_not_invent_actions():
    obs = observation()
    obs["hole"] = ["As", "As"]
    assert [c["intent"] for c in analyze(obs, {})["candidates"]] == ["check"]
    obs["legal"] = []
    assert analyze(obs, {})["candidates"] == []


@pytest.mark.parametrize("seed", [4, 19, 42])
def test_real_tournament_observations_remain_legal_private_and_unmodified(seed):
    game = Tournament("strategy-integration", TournamentConfig(seed=seed, stack_bb=10, hands_per_level=2).model_dump())
    rng = random.Random(seed)
    seen_streets = set()
    for step in range(3000):
        if game.status == "finished":
            break
        if game.phase == "hand_complete":
            game.new_hand()
            continue
        obs = game.observation()
        before = game.snapshot()
        # Exercise the actual assess() interface once per seeded tournament.
        metrics = assess({"observation": obs})["metrics"] if step == 0 else {}
        result = analyze(obs, metrics)
        seen_streets.add(obs["street"])
        assert game.snapshot() == before
        assert result["state_version"] == obs["version"]
        assert result["candidates"]
        available = {e["id"] for e in obs["history"]}
        available.update(e["id"] for p in obs["opponents"] for e in p["recent_actions"])
        for c in result["candidates"]:
            assert c["action"] in {a["key"] for a in obs["legal"]}
            assert set(c["evidence_ids"]) <= available
            assert c["intent"] in {"value", "bluff", "semi_bluff", "check", "call", "fold"}
        json.dumps(result, allow_nan=False)
        # A passive first hand guarantees real decisions on every street; later
        # random legal actions exercise raises, folds, all-ins and elimination.
        action = next(a for a in obs["legal"] if a["kind"] == "call") if game.hand == 1 else rng.choice(obs["legal"])
        game.apply(action["key"], obs["version"])
    assert game.status == "finished"
    assert {"preflop", "flop", "turn", "river"} <= seen_streets
    assert sum(game.stacks) == game.total and sum(game.prizes) == 100
