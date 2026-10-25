"""PokerKit is the only authority for cards, betting legality and settlement."""

from collections import deque
from copy import deepcopy
import random

from pokerkit import Automation, Deck, NoLimitTexasHoldem, calculate_icm

from .tracing import private_observation

AUTOMATIONS = (
    Automation.ANTE_POSTING,
    Automation.BET_COLLECTION,
    Automation.BLIND_OR_STRADDLE_POSTING,
    Automation.CARD_BURNING,
    Automation.HOLE_CARDS_SHOWING_OR_MUCKING,
    Automation.HAND_KILLING,
    Automation.CHIPS_PUSHING,
    Automation.CHIPS_PULLING,
)
STREETS = ("preflop", "flop", "turn", "river")
NAMES = ("Range Agent", "Marlow", "Cleo", "Atlas", "Jules", "Remy")
PROFILES = ("agent", "tight", "caller", "aggressive", "balanced", "volatile")
POSITIONS = {
    6: ["SB", "BB", "UTG", "HJ", "CO", "BTN"],
    5: ["SB", "BB", "HJ", "CO", "BTN"],
    4: ["SB", "BB", "CO", "BTN"],
    3: ["SB", "BB", "BTN"],
    2: ["BB", "BTN / SB"],
}


class Tournament:
    def __init__(self, table_id, config):
        self.id, self.config = table_id, config
        self.rng = random.Random(config["seed"])
        self.stacks = [config["stack_bb"] * 10] * 6
        self.total = sum(self.stacks)
        self.hand, self.version, self.button = 0, 0, 5
        self.status, self.phase = "paused", "ready"
        self.history, self.hand_actions, self.decisions = [], [], []
        self.stats = [
            {"actions": 0, "raises": 0, "folds": 0, "calls": 0} for _ in NAMES
        ]
        self.payouts = [70, 30] if config["payouts"] == "70/30" else [100]
        self.prizes, self.places = [0.0] * 6, [None] * 6
        self.series = [{"hand": 0, "stack": self.stacks[0]}]
        self.last_decision = None
        self.new_hand()

    def log(self, text, player=None, action=None, amount=0):
        e = {
            "id": f"e{len(self.history) + 1}",
            "hand": self.hand,
            "street": self.street,
            "text": text,
            "player": player,
            "action": action,
            "amount": amount,
        }
        self.history.append(e)
        if action:
            self.hand_actions.append(e)

    @property
    def street(self):
        if not hasattr(self, "state") or self.state.street_index is None:
            return "showdown"
        return STREETS[self.state.street_index]

    @property
    def actor(self):
        return (
            self.order[self.state.actor_index]
            if self.state.actor_index is not None
            else None
        )

    def new_hand(self):
        alive = [i for i, v in enumerate(self.stacks) if v > 0]
        if len(alive) == 1:
            self.status, self.phase = "finished", "complete"
            self.places[alive[0]], self.prizes[alive[0]] = 1, self.payouts[0]
            return
        if self.hand:
            self.button = next(
                (self.button + n) % 6
                for n in range(1, 7)
                if (self.button + n) % 6 in alive
            )
        self.hand += 1
        self.level = (self.hand - 1) // self.config["hands_per_level"]
        self.bb = min(self.total, round(10 * 1.5 ** min(self.level, 30)))
        self.sb = max(1, self.bb // 2)
        self.order = [
            (self.button + n) % 6 for n in range(1, 7) if (self.button + n) % 6 in alive
        ]
        self.start_stacks = self.stacks.copy()
        self.hand_actions = []
        self.state = NoLimitTexasHoldem.create_state(
            AUTOMATIONS,
            True,
            0,
            (self.sb, self.bb),
            self.bb,
            [self.stacks[i] for i in self.order],
            len(self.order),
        )
        deck = list(Deck.STANDARD)
        self.rng.shuffle(deck)
        self.state.deck_cards = deque(deck)
        while self.state.can_deal_hole():
            self.state.deal_hole()
        self.holes = {
            seat: list(map(repr, self.state.hole_cards[p]))
            for p, seat in enumerate(self.order)
        }
        self.phase = "playing"
        self.advance()
        self.log(f"Hand {self.hand} begins. Blinds {self.sb}/{self.bb}.")
        if not self.state.status:
            self.settle()

    def advance(self):
        while self.state.status and self.state.actor_index is None:
            if self.state.can_deal_hole():
                self.state.deal_hole()
            elif self.state.can_deal_board():
                self.state.deal_board()
            else:
                raise RuntimeError("PokerKit reached an unhandled operation")

    def legal(self):
        s = self.state
        if s.actor_index is None:
            return []
        actions = []
        call = s.checking_or_calling_amount or 0
        if call and s.can_fold():
            actions.append({"key": "fold", "kind": "fold", "amount": 0})
        if s.can_check_or_call():
            actions.append(
                {"key": "call" if call else "check", "kind": "call", "amount": call}
            )
        if s.can_complete_bet_or_raise_to():
            lo, hi = (
                s.min_completion_betting_or_raising_to_amount,
                s.max_completion_betting_or_raising_to_amount,
            )
            after = s.bets[s.actor_index] + call
            sizes = {
                lo,
                hi,
                *[
                    max(lo, min(hi, after + round((s.total_pot_amount + call) * f)))
                    for f in (0.5, 1)
                ],
            }
            for n in sorted(sizes):
                if s.can_complete_bet_or_raise_to(n):
                    actions.append({"key": f"raise:{n}", "kind": "raise", "amount": n})
        return actions

    def observation(self):
        """Explicit allowlist: never include opponent cards or configured profiles."""
        s = self.state
        if self.actor is None:
            raise ValueError("No decision pending")
        return private_observation(
            {
                "table_id": self.id,
                "hand": self.hand,
                "version": self.version,
                "player": self.actor,
                "position": POSITIONS[len(self.order)][s.actor_index],
                "hole": self.holes[self.actor].copy(),
                "board": list(map(repr, s.get_board_cards(0))),
                "street": self.street,
                "pot": s.total_pot_amount,
                "to_call": s.checking_or_calling_amount or 0,
                "big_blind": self.bb,
                "players": [
                    {
                        "seat": seat,
                        "stack": s.stacks[p],
                        "bet": s.bets[p],
                        "active": s.statuses[p],
                        "position": POSITIONS[len(self.order)][p],
                    }
                    for p, seat in enumerate(self.order)
                ],
                "hand_start_stacks": self.start_stacks.copy(),
                "payouts": self.payouts.copy(),
                "history": deepcopy(self.hand_actions),
                "legal": self.legal(),
                "opponents": [
                    {
                        "seat": i,
                        "name": NAMES[i],
                        **self.stats[i],
                        "recent_actions": deepcopy(
                            [
                                e
                                for e in self.history
                                if e["player"] == i and e["action"]
                            ][-5:]
                        ),
                    }
                    for i in self.order
                    if i != self.actor
                ],
            }
        )

    def apply(self, key, version, decision=None):
        if version != self.version:
            raise ValueError("Stale decision rejected")
        action = next((a for a in self.legal() if a["key"] == key), None)
        if action is None:
            raise ValueError("Illegal action rejected")
        player, before_street = self.actor, self.street
        if action["kind"] == "fold":
            self.state.fold()
        elif action["kind"] == "call":
            self.state.check_or_call()
        else:
            self.state.complete_bet_or_raise_to(action["amount"])
        words = (
            "raises to"
            if action["kind"] == "raise"
            else ("checks" if key == "check" else key + "s")
        )
        self.log(
            f"{NAMES[player]} {words}{' ' + str(action['amount']) if action['amount'] else ''}.",
            player,
            key,
            action["amount"],
        )
        self.history[-1]["street"] = before_street
        stat = self.stats[player]
        stat["actions"] += 1
        if action["kind"] == "raise":
            stat["raises"] += 1
        if key == "fold":
            stat["folds"] += 1
        if key == "call":
            stat["calls"] += 1
        if decision is not None:
            self.last_decision = {
                **decision,
                "hand": self.hand,
                "event_id": self.history[-1]["id"],
                "street": before_street,
            }
            self.decisions.append(self.last_decision)
        self.advance()
        if not self.state.status:
            self.settle()

    def settle(self):
        for p, seat in enumerate(self.order):
            self.stacks[seat] = self.state.stacks[p]
        if sum(self.stacks) != self.total:
            raise RuntimeError("Chip conservation failed")
        self.phase = "hand_complete"
        self.series.append({"hand": self.hand, "stack": self.stacks[0]})
        gains = [
            (i, self.stacks[i] - self.start_stacks[i])
            for i in self.order
            if self.stacks[i] > self.start_stacks[i]
        ]
        self.log(" · ".join(f"{NAMES[i]} +{v}" for i, v in gains) or "Pot split.")
        remaining = sum(v > 0 for v in self.stacks)
        busted = [i for i in self.order if not self.stacks[i]]
        place = remaining + 1
        for stack in sorted({self.start_stacks[i] for i in busted}, reverse=True):
            tied = [i for i in busted if self.start_stacks[i] == stack]
            prize = sum(
                self.payouts[p - 1] if p <= len(self.payouts) else 0
                for p in range(place, place + len(tied))
            ) / len(tied)
            for i in tied:
                self.prizes[i], self.places[i] = prize, place
                self.log(f"{NAMES[i]} eliminated in place {place}.", i)
            place += len(tied)
        if remaining == 1:
            winner = next(i for i, v in enumerate(self.stacks) if v)
            self.prizes[winner], self.places[winner] = self.payouts[0], 1
            self.status, self.phase = "finished", "complete"
            self.log(f"{NAMES[winner]} wins the tournament.", winner)

    def snapshot(self):
        players = []
        for i, name in enumerate(NAMES):
            p = self.order.index(i) if i in self.order else None
            live = p is not None and self.state.status
            last = next(
                (e for e in reversed(self.hand_actions) if e["player"] == i), None
            )
            players.append(
                {
                    "seat": i,
                    "name": name,
                    "stack": self.state.stacks[p] if live else self.stacks[i],
                    "bet": self.state.bets[p] if live else 0,
                    "cards": self.holes.get(i, []),
                    "active": bool(self.state.statuses[p])
                    if live
                    else bool(self.stacks[i]),
                    "eliminated": self.places[i] is not None and self.places[i] != 1,
                    "position": POSITIONS[len(self.order)][p]
                    if p is not None
                    else "OUT",
                    "last_action": last["action"] if last else None,
                    "stats": self.stats[i].copy(),
                    "prize": self.prizes[i],
                    "place": self.places[i],
                }
            )
        icm_stacks = self.start_stacks if self.state.status else self.stacks
        alive = [i for i, v in enumerate(icm_stacks) if v > 0]
        vals = calculate_icm(self.payouts, [icm_stacks[i] for i in alive])
        icm = dict(zip(alive, vals))
        return {
            "id": self.id,
            "config": self.config,
            "version": self.version,
            "status": self.status,
            "phase": self.phase,
            "hand": self.hand,
            "street": self.street,
            "level": self.level + 1,
            "small_blind": self.sb,
            "big_blind": self.bb,
            "hands_to_level": self.config["hands_per_level"]
            - (self.hand - 1) % self.config["hands_per_level"],
            "button": self.button,
            "actor": self.actor,
            "players": players,
            "pot": self.state.total_pot_amount,
            "board": list(map(repr, self.state.get_board_cards(0))),
            "history": deepcopy(self.history[-120:]),
            "decision": deepcopy(self.last_decision),
            "series": self.series[-300:],
            "icm": {str(i): round(icm.get(i, self.prizes[i]), 2) for i in range(6)},
            "icm_basis": "Hand-start stacks" if self.state.status else "Settled stacks",
            "agent_decisions": len(self.decisions),
            "remaining": sum(v > 0 for v in self.stacks),
        }
