"""Private opponent controller. Policies receive observations, never Tournament.

This module is not an agent tool or a source of hero evidence. All statistical
memory is built from public decisions, separately for each tournament.
"""

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import random
import secrets
import subprocess

from .tracing import private_observation

REVISION = "0a7dceb575d8b9dfcbd7c46ec7a90482cbdb40ba"
BINARY = Path(__file__).resolve().parents[3] / "native/pokerth/build/pokerth-opponent"
SETUP_ERROR = "PokerTH is unavailable. Run python3 scripts/build_pokerth.py from the repository root."
# These are private demo personalities, not claims about human playing styles.
PERSONALITIES = (
    (0.80, 0.85, 0.65),
    (1.20, 0.80, 0.75),
    (1.05, 1.25, 1.30),
    (1.00, 1.00, 1.00),
    (1.20, 1.15, 1.25),
)
LEGACY_PROFILES = ("tight", "caller", "aggressive", "balanced", "volatile")


class OpponentError(ValueError):
    """Safe controller-facing error, never includes policy inputs."""


def executable():
    return Path(os.environ.get("POKERTH_BINARY", str(BINARY)))


def require_native():
    binary = executable()
    try:
        result = subprocess.run(
            [str(binary), "--version"],
            capture_output=True,
            timeout=2,
            check=True,
            text=True,
        )
        if result.stdout.strip() != f"wtr-pokerth-1 {REVISION}":
            raise ValueError("version")
    except (OSError, subprocess.SubprocessError, ValueError):
        raise OpponentError(SETUP_ERROR) from None
    return binary


def resolve_seeds(config):
    """Controller-only, persisted for replay/reproduction, never in observation."""
    return {
        **config,
        **{
            name: config.get(name)
            if config.get(name) is not None
            else secrets.randbelow(2**31)
            for name in ("opponent_seed", "personality_seed", "hero_seed")
        },
    }


def seat_rng(seed, seat):
    digest = hashlib.sha256(f"wtr-opponent-v1:{seed}:{seat}".encode()).digest()
    return random.Random(int.from_bytes(digest, "big"))


@dataclass
class PublicStat:
    preflop_opportunities: int = 0
    vpip: int = 0
    postflop_actions: int = 0
    postflop_aggression: int = 0
    last_preflop_hand: int = -1
    last_vpip_hand: int = -1


class PublicStats:
    def __init__(self):
        self.players = [PublicStat() for _ in range(6)]

    def observe(self, obs, key):
        """Count one preflop opportunity per hand with a voluntary decision.

        Forced blinds/all-ins do not count. VPIP means at least one paid call or
        raise that hand. Postflop denominator is every voluntary decision,
        including checks and folds; numerator is bets/raises.
        """
        stat = self.players[obs["player"]]
        if obs["street"] == "preflop":
            if stat.last_preflop_hand != obs["hand"]:
                stat.preflop_opportunities += 1
                stat.last_preflop_hand = obs["hand"]
            if (
                key == "call" or key.startswith("raise:")
            ) and stat.last_vpip_hand != obs["hand"]:
                stat.vpip += 1
                stat.last_vpip_hand = obs["hand"]
        else:
            stat.postflop_actions += 1
            stat.postflop_aggression += key.startswith("raise:")

    def percentages(self, seats):
        stats = [self.players[s] for s in seats]
        opportunities = sum(s.preflop_opportunities for s in stats)
        actions = sum(s.postflop_actions for s in stats)
        # Ten observed opportunities in the active-opponent pool before using a rate.
        return (
            round(100 * sum(s.vpip for s in stats) / opportunities)
            if opportunities >= 10
            else -1,
            round(100 * sum(s.postflop_aggression for s in stats) / actions)
            if actions >= 10
            else -1,
        )


def card_number(card):
    # Upstream uses rank within suit. Suit permutation does not affect its logic.
    if (
        not isinstance(card, str)
        or len(card) != 2
        or card[0] not in "23456789TJQKA"
        or card[1] not in "cdhs"
    ):
        raise OpponentError("Invalid PokerTH card")
    return "cdhs".index(card[1]) * 13 + "23456789TJQKA".index(card[0])


def situation(obs, stats):
    """Translate only permitted public facts and the acting player's cards."""
    obs = private_observation(obs)
    players = obs["players"]
    actor = next(p for p in players if p["seat"] == obs["player"])
    opponents = [p for p in players if p["active"] and p["seat"] != obs["player"]]
    street = ("preflop", "flop", "turn", "river").index(obs["street"])
    cards = [card_number(c) for c in obs["hole"] + obs["board"]]
    if (
        len(obs["hole"]) != 2
        or len(obs["board"]) != (0 if street == 0 else street + 2)
        or len(set(cards)) != len(cards)
    ):
        raise OpponentError("Invalid PokerTH cards or street")
    history = [e for e in obs["history"] if e["street"] == obs["street"]]
    latest = {e["player"]: e["action"] for e in history}
    # Upstream counts opponents who have not acted on this street, including
    # blind posters preflop, but excluding folded/all-in players.
    behind = sum(p["stack"] > 0 and p["seat"] not in latest for p in opponents)
    highest = max(p["bet"] for p in players)
    bets = sum(p["bet"] for p in players)
    raises = [a["amount"] for a in obs["legal"] if a["kind"] == "raise"]
    minimum = max(1, min(raises) - highest) if raises else obs["big_blind"]
    # Match upstream's latest-action count, not a count of every historical raise.
    raised = sum(
        p["stack"] > 0 and latest.get(p["seat"], "").startswith("raise:")
        for p in players
    )
    vpip, aggression = stats.percentages([p["seat"] for p in opponents])
    return [
        street,
        *cards,
        actor["stack"],
        actor["bet"],
        highest,
        minimum,
        max(1, obs["big_blind"] // 2),
        obs["pot"] - bets,
        bets,
        len(opponents),
        behind,
        max((p["stack"] + p["bet"] for p in opponents), default=0),
        raised,
        int(actor["position"] == "BB"),
        vpip,
        aggression,
    ]


def parse_decision(output):
    try:
        if len(output) > 100:
            raise ValueError()
        parts = output.split()
        if len(parts) != 3 or any(not p.isascii() or not p.isdecimal() for p in parts):
            raise ValueError()
        action, bet, increment = map(int, parts)
        if (
            not 1 <= action <= 6
            or not 0 <= bet <= 20000000
            or not 0 <= increment <= 20000000
        ):
            raise ValueError()
        return action, bet, increment
    except (ValueError, TypeError, AttributeError):
        raise OpponentError("PokerTH returned an invalid decision") from None


def normalize(obs, decision):
    action, bet, increment = decision
    legal = obs["legal"]
    passive = next((a["key"] for a in legal if a["kind"] == "call"), None)
    if passive is None:
        raise OpponentError("PokerTH observation has no check/call action")
    if action == 1:
        return "fold" if any(a["key"] == "fold" for a in legal) else passive
    if action in (2, 3):
        return passive
    raises = [a for a in legal if a["kind"] == "raise"]
    if not raises:
        return passive  # Covers a short all-in that did not reopen action.
    actor = next(p for p in obs["players"] if p["seat"] == obs["player"])
    target = bet if action == 4 else max(p["bet"] for p in obs["players"]) + increment
    if action == 6:
        target = actor["stack"] + actor["bet"]
    target = min(target, actor["stack"] + actor["bet"])
    # Nearest legal raise-to, lower size wins ties. PokerKit supplied every option.
    return min(raises, key=lambda a: (abs(a["amount"] - target), a["amount"]))["key"]


class Opponents:
    def __init__(self, config, profiles=LEGACY_PROFILES):
        self.mode = config.get("opponents", "legacy")
        if self.mode not in ("legacy", "pokerth"):
            raise OpponentError("Unknown opponent policy")
        self.binary = require_native() if self.mode == "pokerth" else None
        seeds = resolve_seeds(config)
        self.random = {
            seat: seat_rng(seeds["opponent_seed"], seat) for seat in range(1, 6)
        }
        self.personalities = list(PERSONALITIES)
        self.profiles = list(profiles)
        assignments = random.Random(seeds["personality_seed"])
        assignments.shuffle(self.personalities)
        assignments.shuffle(self.profiles)
        self.stats = PublicStats()

    def decide(self, observation):
        obs = private_observation(observation)
        seat = obs["player"]
        if seat not in self.random:
            raise OpponentError("Opponent policy received the hero seat")
        if self.mode == "legacy":
            from .agent import assess, baseline

            return baseline(
                obs,
                assess({"observation": obs})["metrics"],
                self.random[seat],
                self.profiles[seat - 1],
            )
        values = [
            self.random[seat].getrandbits(64),
            *situation(obs, self.stats),
            *self.personalities[seat - 1],
        ]
        request = " ".join(map(str, values)) + "\n"
        if len(request) > 1024:
            raise OpponentError("PokerTH input exceeds limit")
        try:
            result = subprocess.run(
                [str(self.binary)],
                input=request,
                capture_output=True,
                text=True,
                timeout=2,
                check=True,
            )
        except subprocess.TimeoutExpired:
            raise OpponentError("PokerTH decision timed out") from None
        except (OSError, subprocess.SubprocessError):
            raise OpponentError(
                "PokerTH decision failed; check the native build"
            ) from None
        return normalize(obs, parse_decision(result.stdout))

    def observe(self, obs, key):
        self.stats.observe(obs, key)
