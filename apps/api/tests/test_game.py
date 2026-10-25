import random
import pytest

from wtr.game import Tournament
from wtr.models import TournamentConfig


def game(seed=42):
    return Tournament(
        "test", TournamentConfig(seed=seed, stack_bb=10, hands_per_level=2).model_dump()
    )


@pytest.mark.parametrize("seed", range(8))
def test_complete_tournament_conserves_chips_and_pays_out(seed):
    g, rng = game(seed), random.Random(seed)
    for _ in range(3000):
        snap = g.snapshot()
        assert sum(p["stack"] for p in snap["players"]) + snap["pot"] == g.total
        if g.status == "finished":
            break
        if g.phase == "hand_complete":
            g.new_hand()
            continue
        actions = g.legal()
        g.apply(rng.choice(actions)["key"], g.version)
    assert g.status == "finished"
    assert sum(g.prizes) == 100
    assert sum(s > 0 for s in g.stacks) == 1
    assert max(g.stacks) == g.total


def test_private_observation_does_not_include_other_hole_cards_or_profiles():
    g = game()
    obs = g.observation()
    assert obs["hole"] == g.holes[g.actor]
    assert all(
        set(p) == {"seat", "stack", "bet", "active", "position"} for p in obs["players"]
    )
    assert "profiles" not in obs and "cards" not in obs
    assert all("cards" not in p and "profile" not in p for p in obs["opponents"])


def test_stale_or_illegal_decisions_do_not_mutate_game():
    g = game()
    before = g.snapshot()
    with pytest.raises(ValueError, match="Stale"):
        g.apply("fold", -1)
    with pytest.raises(ValueError, match="Illegal"):
        g.apply("raise:999999", g.version)
    assert g.snapshot() == before


def test_heads_up_button_posts_small_blind_and_acts_first():
    g = game()
    g.stacks = [100, 0, 100, 0, 0, 0]
    g.total = 200
    g.button = 5
    g.new_hand()
    assert g.order == [2, 0]
    assert g.button == 0
    assert g.actor == 0
    assert g.state.bets == [g.bb, g.sb]


def test_same_seed_and_actions_reproduce_cards():
    a, b = game(), game()
    for _ in range(30):
        assert a.snapshot() == b.snapshot()
        if a.status == "finished":
            break
        if a.phase == "hand_complete":
            a.new_hand()
            b.new_hand()
        else:
            key = a.legal()[-1]["key"]
            a.apply(key, a.version)
            b.apply(key, b.version)
