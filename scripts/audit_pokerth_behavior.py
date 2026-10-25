"""Controller-only behavior audit. Never imported by the playing agent."""
import asyncio
from collections import Counter, defaultdict
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys

os.environ.update(LANGSMITH_TRACING="false", LANGCHAIN_TRACING_V2="false")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))

from pokerkit import StandardHighHand
from wtr.agent import Agent
from wtr.game import Tournament
from wtr.models import TournamentConfig
from wtr.opponents import Opponents, parse_decision

OUT = ROOT / "apps/api/data/pokerth-review-20261025"
OUT.mkdir(parents=True, exist_ok=True)
original_run = subprocess.run
last_native = None
last_request = None


def capture_result(*args, **kwargs):
    global last_native, last_request
    result = original_run(*args, **kwargs)
    if "input" in kwargs:
        last_native = parse_decision(result.stdout)
        last_request = kwargs["input"]
    return result


subprocess.run = capture_result


async def audit():
    rows, runs, position_checks = [], [], []
    for index, deck in enumerate((42, 7, 101, 107, 1, 19)):
        cfg = TournamentConfig(
            opponents="pokerth", seed=deck, hero_seed=42 + index,
            opponent_seed=43 + 17 * index, personality_seed=44 + 19 * index,
            stack_bb=100, hands_per_level=100,
        ).model_dump()
        game = Tournament("opaque", cfg)
        opponents = Opponents(cfg)
        agent = Agent("heuristic", seed=cfg["hero_seed"])
        game.version = 1
        actions = 0
        try:
            while game.status != "finished" and game.hand <= 25:
                assert sum(game.state.stacks) + game.state.total_pot_amount == game.total
                assert min(game.state.stacks) >= 0
                if game.phase == "hand_complete":
                    if game.hand == 25:
                        break
                    game.new_hand()
                    game.version += 1
                    continue
                obs = game.observation()
                actor = next(p for p in obs["players"] if p["seat"] == obs["player"])
                row = {"run": index + 1, "hand": game.hand, "player": obs["player"],
                       "street": obs["street"], "hole": obs["hole"], "board": obs["board"],
                       "position": obs["position"], "pot": obs["pot"], "to_call": obs["to_call"],
                       "stack": actor["stack"], "bet": actor["bet"], "bb": obs["big_blind"],
                       "players": deepcopy(obs["players"]), "history": deepcopy(obs["history"]),
                       "legal": obs["legal"]}
                if obs["board"]:
                    row["made_hand"] = str(StandardHighHand.from_game("".join(obs["hole"]), "".join(obs["board"])))
                if obs["player"] == 0:
                    decision = await agent.decide(obs)
                    key = decision["action"]
                else:
                    key = opponents.decide(obs)
                    row["native"] = last_native
                    # Hold cards, native RNG and personality fixed. Only change the
                    # position proxy for the reproduced small-blind reraise spots.
                    if index == 0 and game.hand == 8 and obs["player"] == 1 and obs["to_call"] in (30, 180):
                        fields = last_request.split()
                        behind_index = 12 + len(obs["board"])
                        old_behind = fields[behind_index]
                        fields[behind_index] = "1"
                        alternate = original_run(
                            [str(opponents.binary)], input=" ".join(fields) + "\n",
                            text=True, capture_output=True, check=True, timeout=2,
                        )
                        position_checks.append({
                            "hand": 8, "position": obs["position"], "hole": obs["hole"],
                            "to_call": obs["to_call"], "opponents_behind": int(old_behind),
                            "actual_native": last_native,
                            "with_one_opponent_behind": parse_decision(alternate.stdout),
                            "executed": key,
                        })
                    native_action, bet, increment = last_native
                    if native_action >= 4:
                        target = bet if native_action == 4 else max(p["bet"] for p in obs["players"]) + increment
                        if native_action == 6:
                            target = actor["stack"] + actor["bet"]
                        row["target"] = min(target, actor["stack"] + actor["bet"])
                row["action"] = key
                assert key in [a["key"] for a in obs["legal"]]
                game.apply(key, obs["version"])
                opponents.observe(obs, key)
                game.version += 1
                actions += 1
                assert sum(game.state.stacks) + game.state.total_pot_amount == game.total
                rows.append(row)
            runs.append({"run": index + 1, "config": cfg, "hands": game.hand,
                         "actions": actions, "finished": game.status == "finished",
                         "chip_total": sum(game.state.stacks) + game.state.total_pot_amount})
            print(json.dumps(runs[-1]), flush=True)
        finally:
            agent.close()

    native = [r for r in rows if r["player"] != 0]
    counts = {s: dict(Counter(r["action"].split(":")[0] for r in native if r["street"] == s))
              for s in ("preflop", "flop", "turn", "river")}
    opportunities = defaultdict(lambda: {"hands": set(), "vpip": set(), "pfr": set()})
    for r in native:
        if r["street"] != "preflop":
            continue
        k = (r["run"], r["hand"], r["player"])
        p = opportunities[r["position"]]
        p["hands"].add(k)
        if r["action"] == "call" or r["action"].startswith("raise:"):
            p["vpip"].add(k)
        if r["action"].startswith("raise:"):
            p["pfr"].add(k)
    sizes = [r for r in native if r["action"].startswith("raise:") and "target" in r]
    changed = [r for r in sizes if int(r["action"].split(":")[1]) != r["target"]]
    summary = {"runs": len(runs), "hands": sum(r["hands"] for r in runs), "actions": len(rows),
               "native_decisions": len(native), "native_counts": counts,
               "chip_conservation_passed": True, "illegal_actions": 0,
               "position_stats": {p: {k: len(v) for k, v in stats.items()} for p, stats in opportunities.items()},
               "native_aggressive_actions": len(sizes), "sizing_adjusted": len(changed),
               "sizing_changed_over_20_percent": sum(abs(int(r["action"].split(":")[1]) - r["target"]) / max(1, r["target"]) > 0.2 for r in sizes),
               "no_legal_raise_normalizations": sum("target" in r and not r["action"].startswith("raise:") for r in native),
               "postflop_hands": len({(r["run"], r["hand"]) for r in rows if r["street"] != "preflop"}),
               "street_hand_counts": {s: len({(r["run"], r["hand"]) for r in rows if r["street"] == s})
                                      for s in ("preflop", "flop", "turn", "river")}}
    (OUT / "audit.json").write_text(json.dumps({"summary": summary, "runs": runs, "position_checks": position_checks, "actions": rows}, indent=2) + "\n")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    asyncio.run(audit())
