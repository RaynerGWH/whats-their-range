"""Small, conditional hypotheses over the existing private observation contract."""

from collections import Counter
from math import isfinite

from pokerkit import StandardHighHand


_RANKS = "23456789TJQKA"
_LABELS = (
    "High card", "One pair", "Two pair", "Three of a kind", "Straight",
    "Flush", "Full house", "Four of a kind", "Straight flush",
)
_BASE_LIMITATIONS = (
    "No calibrated opponent ranges or response probabilities are available.",
    "Candidate intents are heuristic hypotheses, not solved action values or frequencies.",
    "ICM at hand start is descriptive; tournament action values are not modeled.",
    "The observation has no pot eligibility map; full-pot calculations are conditional.",
)


def _quantity(value, unit, basis, *assumptions):
    return {"value": value, "unit": unit, "basis": basis, "assumptions": list(assumptions)}


def _probability(value):
    return (
        isinstance(value, (int, float)) and not isinstance(value, bool)
        and isfinite(value) and 0 <= value <= 1
    )


def _hand_features(hole, board):
    """Describe only visible cards. Direct draws are not clean winning outs."""
    cards = hole + board
    if (
        len(hole) != 2 or len(board) not in (0, 3, 4, 5)
        or any(not isinstance(c, str) or len(c) != 2
               or c[0] not in _RANKS or c[1] not in "cdhs" for c in cards)
        or len(set(cards)) != len(cards)
    ):
        return "Unavailable hand features", None, []

    own = [_RANKS.index(c[0]) + 2 for c in hole]
    public = [_RANKS.index(c[0]) + 2 for c in board]
    if not board:
        premium = own[0] == own[1] and own[0] >= 12 or set(own) == {13, 14}
        return "Preflop private cards", "value" if premium else None, []

    hand = StandardHighHand.from_game("".join(hole), "".join(board))
    label = hand.entry.label.value
    rank = _LABELS.index(label)
    counts = sorted(Counter(public).values(), reverse=True)
    # Before the river the public cards alone can only make duplicate-rank features.
    public_rank = {4: 7, 3: 3, 2: 1, 1: 0}[counts[0]]
    if counts[:2] == [2, 2]:
        public_rank = 2
    improves_board = rank > public_rank
    if len(board) == 5:
        improves_board = hand > StandardHighHand.from_game("", "".join(board))
    top_pair = max(public) in own and public.count(max(public)) == 1
    overpair = own[0] == own[1] and own[0] > max(public)
    value = improves_board and (rank >= 2 or top_pair or overpair)

    draws = []
    if len(board) < 5 and rank < 4:
        suits = Counter(c[1] for c in cards)
        if any(n == 4 and any(c[1] == suit for c in hole) for suit, n in suits.items()):
            draws.append("four-card flush draw using a private card")
        ranks, board_ranks = set(own + public), set(public)
        if 14 in ranks:
            ranks.add(1)
        if 14 in board_ranks:
            board_ranks.add(1)
        for low in range(1, 11):
            window = set(range(low, low + 5))
            if len(window & ranks) == 4 and (window & ranks) - board_ranks:
                draws.append("one-card straight completion using a private rank")
                break
    intent = "value" if value else "semi_bluff" if draws else "bluff"
    return label, intent, draws


def _evidence(observation, opponent_seats):
    """Use structured facts, never echo arbitrary event text or simulator metadata."""
    events = list(observation.get("history", []))
    for opponent in observation.get("opponents", []):
        if opponent.get("seat") in opponent_seats:
            events.extend(opponent.get("recent_actions", []))
    ids = {
        event["id"] for event in events
        if event.get("player") in opponent_seats
        and isinstance(event.get("id"), str) and 0 < len(event["id"]) <= 160
        and (event.get("action") in ("fold", "call", "check")
             or (isinstance(event.get("action"), str)
                 and event["action"].startswith("raise:")
                 and event["action"][6:].isdigit()))
    }
    street_raises = [
        event for event in observation.get("history", [])
        if event.get("id") in ids
        and event.get("hand") == observation["hand"]
        and event.get("street") == observation["street"]
        and event["action"].startswith("raise:")
    ]
    return len(ids), list(dict.fromkeys(e["id"] for e in street_raises))[-10:]


def analyze(observation: dict, metrics: dict) -> dict:
    """Return strategy contract v1 candidates without selecting or applying an action.

    Expects Tournament.observation(), never a spectator snapshot, and metrics from
    assess(). Missing evidence/metrics are supported. Core state fields are required.
    Unknown fields are ignored rather than copied into the result.
    """
    obs = observation
    hero = next(p for p in obs["players"] if p["seat"] == obs["player"])
    opponents = [p for p in obs["players"] if p["active"] and p["seat"] != obs["player"]]
    count, raise_ids = _evidence(obs, {p["seat"] for p in opponents})
    label, raise_intent, draws = _hand_features(list(obs["hole"]), list(obs["board"]))
    uncertainty = list(_BASE_LIMITATIONS)
    uncertainty.append(
        f"{'Sparse' if count < 2 else 'Bounded'} evidence: {count} distinct public opponent actions; "
        "counts lack matched opportunities and do not establish a tendency."
    )
    if len(opponents) > 1:
        uncertainty.append("Multiway pot: joint responses are unknown; do not multiply assumed individual fold rates.")
    visible_all_in = any(p["active"] and p["stack"] == 0 for p in obs["players"])
    if visible_all_in:
        uncertainty.append("An active player is already all-in; folds cannot award the entire pot uncontested.")
    effective = [min(hero["stack"], max(0, p["stack"] + p["bet"] - hero["bet"])) for p in opponents]
    if effective and min(effective) <= 10 * obs["big_blind"]:
        uncertainty.append("Short effective stack (at most 10 big blinds): future betting room is limited; no push/fold solution is available.")
    if raise_intent is None:
        uncertainty.append("Raise intents are omitted where visible features do not support this module's limited classification.")
    if draws:
        uncertainty.append("Draw completions can be dominated or shared; no clean outs, draw probability, or equity realization is estimated.")

    # Position labels alone do not encode who still has an action in this round.
    position = obs["position"] if obs["position"] in {"SB", "BB", "UTG", "HJ", "CO", "BTN", "BTN / SB"} else "unknown"
    context = f"{label}; position {position}; {len(opponents)} active opponents; pot {obs['pot']} chips."
    if raise_ids:
        context += f" The supplied current-street history contains {len(raise_ids)} cited opponent raises."
    uncertainty.append("Position is a seat label; remaining action order and future responses are not reconstructed.")

    candidates = []
    for action in obs["legal"]:
        kind = action["kind"]
        if kind == "raise" and (raise_intent is None or not opponents):
            continue
        if kind not in ("fold", "call", "raise"):
            continue
        intent = raise_intent if kind == "raise" else ("check" if kind == "call" and action["amount"] == 0 else kind)
        estimates = {}
        assumptions = ["The supplied private observation and legal menu describe the same state version."]
        limitations = list(uncertainty)
        if effective:
            estimates["effective_commitment"] = _quantity(
                [{"seat": p["seat"], "chips": n} for p, n in zip(opponents, effective)],
                "chips", "min(hero stack, opponent stack + opponent street bet - hero street bet), floored at zero",
                "Pairwise additional matched exposure from this decision, not side-pot eligibility or a multiway action value.",
            )
        if _probability(metrics.get("equity")):
            estimates["random_range_equity_reference"] = _quantity(
                metrics["equity"], "fraction of pot", "Supplied baseline Monte Carlo estimate",
                "Uniform random opponent hands and a completed board, not the range that continues against this action.",
            )
            if _probability(metrics.get("standard_error")):
                estimates["sampling_standard_error"] = _quantity(
                    metrics["standard_error"], "fraction of pot", "Supplied Monte Carlo standard error",
                    "Sampling error excludes range-model error and is not confidence in this candidate.",
                )
        else:
            limitations.append("No valid random-range equity metric was supplied; equity is not inferred from action counts.")

        if intent == "fold":
            reason = "Decline additional exposure while facing a wager; prior commitments are sunk."
            continuation = "No further decisions in this hand after folding."
        elif intent == "check":
            reason = "Retain the hand without committing chips now; checking does not guarantee a free showdown."
            continuation = "Reassess only if another decision occurs, using its new observation and legal menu."
        elif intent == "call":
            reason = f"Continue for {action['amount']} additional chips without assuming the supplied equity is realized."
            continuation = "If action remains, reassess the next observed state; no automatic future call or raise is implied."
            if len(opponents) == 1 and not visible_all_in and obs["pot"] + action["amount"] > 0:
                estimates["checkdown_call_share_required"] = _quantity(
                    action["amount"] / (obs["pot"] + action["amount"]), "fraction of final pot",
                    "call / (current pot + call), break-even against folding",
                    "Hero is eligible for the whole pot; no side pots or unreturned excess bets.",
                    "No further wagers or costs; chip value only, not tournament prize value.",
                )
            else:
                limitations.append("Call threshold withheld because multiway or all-in pot eligibility is unresolved.")
        else:
            risk = action["amount"] - hero["bet"]
            estimates["additional_commitment"] = _quantity(
                risk, "chips", "legal raise-to amount minus hero's current street bet",
                "Quoted commitment before any return of unmatched chips.",
            )
            if intent == "value":
                reason = "Visible private-card strength supports a value hypothesis only if worse hands continue at this size."
                assumptions.append("Worse hands sometimes continue; their frequency and the value of this size are unknown.")
                continuation = "If called or raised, reassess public cards and sizing; this label does not commit to stacking off."
            elif intent == "semi_bluff":
                reason = "Consider fold pressure with a " + " and a ".join(draws) + "."
                assumptions.append("Some opponents can fold, and a draw completion may help if called; neither rate is calibrated.")
                continuation = "If called, reassess the observed next card and betting; a completion need not win, and a miss does not imply another barrel."
            else:
                reason = "Consider a bluff hypothesis that depends on folds; limited made strength alone does not establish profitability."
                assumptions.append("Fold pressure is hypothetical. Zero showdown return is a comparison model, not a claim that these cards have no equity.")
                continuation = "If continued against, reassess or give up under the next legal menu; no future bluff is precommitted."
            if intent in ("bluff", "semi_bluff"):
                supported = (
                    len(opponents) == 1 and not visible_all_in and obs["pot"] > 0 and risk > 0
                    and action["amount"] <= opponents[0]["stack"] + opponents[0]["bet"]
                )
                if supported:
                    estimates["zero_equity_fold_rate_required"] = _quantity(
                        risk / (obs["pot"] + risk), "fraction of responses",
                        "risk / (pot + risk), from f * pot - (1 - f) * risk = 0",
                        "Heads-up, entire pot eligible, no side pots or unreturned excess bets.",
                        "Any continuation loses this additional commitment; zero showdown return and no further investment.",
                        "Compared with surrendering this pot, not checking or calling; chip value only.",
                    )
                    limitations.append("Required fold rate is a conditional threshold, not a predicted response or recommended bluff frequency.")
                else:
                    limitations.append("Fold threshold withheld for multiway, existing all-in, unmatched sizing, or unavailable positive pot/risk.")
        candidates.append({
            "action": action["key"], "intent": intent, "rationale": context + " " + reason,
            "evidence_ids": list(raise_ids), "assumptions": assumptions,
            "limitations": limitations, "estimates": estimates, "continuation": continuation,
        })
    return {"schema_version": 1, "state_version": obs["version"], "candidates": candidates, "uncertainty": uncertainty}
