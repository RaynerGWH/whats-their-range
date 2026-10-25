"""Summarize recorded native smoke runs and extract public hand examples."""

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "apps/api/data/stage2a"
OUT = ROOT / "docs/review"


def main():
    sets, public_hands = [], []
    for name in ("native-set-a", "native-set-b", "native-standard"):
        source = DATA / name / "results.json"
        report = json.loads(source.read_text())
        rows = report["results"]
        assert all(r["status"] == "completed" and r["chip_conservation"] for r in rows)
        assert all(
            rows[i]["outcome_sha256"] == rows[i + 1]["outcome_sha256"]
            for i in range(0, len(rows), 2)
        )
        actions = [a for r in rows for a in r["action_records"]]
        sets.append(
            {
                "set": name,
                "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "config": report["config"],
                "runtime": report["runtime"],
                "games": len(rows),
                "hands": sum(r["hands"] for r in rows),
                "actions": len(actions),
                "hero_decisions": sum(r["hero_decisions"] for r in rows),
                "native_decisions": sum(a["player"] != 0 for a in actions),
                "matching_repeat_pairs": len(rows) // 2,
                "streets": dict(Counter(a["street"] for a in actions)),
                "player_counts": sorted({len(a["players"]) for a in actions}),
                "runs": [
                    {
                        k: r[k]
                        for k in (
                            "seed",
                            "repeat",
                            "split",
                            "opponent_seed",
                            "personality_seed",
                            "hands",
                            "actions",
                            "outcome_sha256",
                            "chip_total",
                            "chip_conservation",
                        )
                    }
                    for r in rows
                ],
            }
        )
        # One multi-street public hand and one heads-up hand per set, from first repeats.
        candidates = []
        for row in rows[::2]:
            hands = defaultdict(list)
            for action in row["action_records"]:
                hands[action["hand"]].append(action)
            for hand, records in hands.items():
                candidates.append((row, hand, records))
        selections = [
            max(
                candidates, key=lambda c: (len({a["street"] for a in c[2]}), len(c[2]))
            ),
            next(c for c in candidates if len(c[2][0]["players"]) == 2),
        ]
        for kind, (row, hand, records) in zip(("multi-street", "heads-up"), selections):
            public_hands.append(
                {
                    "case": f"{name}-{kind}",
                    "outcome_sha256": row["outcome_sha256"],
                    "hand": hand,
                    "records": [
                        {
                            k: a[k]
                            for k in (
                                "state_version",
                                "player",
                                "street",
                                "board",
                                "pot",
                                "players",
                                "legal_actions",
                                "action",
                            )
                        }
                        for a in records
                    ],
                }
            )
    summary = {
        "schema_version": 1,
        "description": "Real PokerTH opponents, heuristic hero. Repeats are not independent samples.",
        "build": json.loads((ROOT / "native/pokerth/build/build.json").read_text()),
        "sets": sets,
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "stage-2a-smoke.json").write_text(json.dumps(summary, indent=2) + "\n")
    (OUT / "stage-2a-hands.json").write_text(json.dumps(public_hands, indent=2) + "\n")
    lines = [
        "# Stage 2A public hand examples",
        "",
        "Recorded legal play against real native PokerTH opponents and the heuristic hero. These are execution examples, not approved strategy. No opponent hole cards, personalities or native private inputs are included. Raise amounts are street totals. Cases come from the recorded smoke sets; reproduction settings are in stage-2a-smoke.json.",
    ]
    for case in public_hands:
        lines += [
            "",
            f"## {case['case']}, hand {case['hand']}",
            "",
            "| Version | Street | Board | Pot before | Player | Action |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for r in case["records"]:
            lines.append(
                f"| {r['state_version']} | {r['street']} | {' '.join(r['board']) or '(none)'} | {r['pot']} | {'Hero' if r['player'] == 0 else 'Player ' + str(r['player'] + 1)} | {r['action']} |"
            )
    (OUT / "stage-2a-hands.md").write_text("\n".join(lines) + "\n")
    print(
        {
            key: sum(s[key] for s in sets)
            for key in (
                "games",
                "hands",
                "actions",
                "hero_decisions",
                "native_decisions",
                "matching_repeat_pairs",
            )
        }
    )


if __name__ == "__main__":
    main()
