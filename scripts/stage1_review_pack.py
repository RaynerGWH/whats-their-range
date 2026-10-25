"""Generate review observations through legal play, without hidden-state fixtures.

Run with apps/api/.venv/bin/python scripts/stage1_review_pack.py.
The controller recipe below is never supplied to a playing policy.
"""

import hashlib
import json
from pathlib import Path

from wtr.agent import assess
from wtr.game import Tournament
from wtr.models import TournamentConfig
from wtr.strategy import analyze

ROOT = Path(__file__).resolve().parents[1]
RECIPES = ((42, 50, "passive"), (8, 50, "passive"), (7, 10, "pressure"))


def build_pack():
    cases = []
    for index, (deck_seed, stack_bb, line) in enumerate(RECIPES):
        # Opaque fixed review ID, unrelated to the private deck seed.
        game = Tournament(
            f"{index + 1:032x}",
            TournamentConfig(seed=deck_seed, stack_bb=stack_bb).model_dump(),
        )
        game.version += 1
        while game.hand == 1 and game.actor is not None:
            obs = game.observation()
            if obs["player"] == 0:
                metrics = assess({"observation": obs})["metrics"]
                candidates = analyze(obs, metrics)
                questions = [
                    "Which public actions support a range hypothesis, and which reads remain unsupported?",
                    "Which legal size or passive action would you compare, and what response assumptions does that require?",
                ]
                if len(obs["board"]) < 5:
                    questions.append(
                        "What next-street observations would change the plan, without assuming a future card?"
                    )
                if any(p["active"] and p["stack"] == 0 for p in obs["players"]):
                    questions.append(
                        "How should side-pot eligibility and tournament payouts limit the equity reference?"
                    )
                cases.append(
                    {
                        "case_id": f"review-{len(cases) + 1:02d}",
                        "observation": obs,
                        "metrics": metrics,
                        "candidate_hypotheses": [
                            {
                                "action": c["action"],
                                "intent": c["intent"],
                                "assumptions": c["assumptions"],
                            }
                            for c in candidates["candidates"]
                        ],
                        "limitations": candidates["uncertainty"],
                        "discussion_points": questions,
                    }
                )
            raises = [a for a in obs["legal"] if a["kind"] == "raise"]
            if line == "pressure" and obs["player"] != 0 and raises:
                key = max(raises, key=lambda a: a["amount"])["key"]
            else:
                key = next(a["key"] for a in obs["legal"] if a["kind"] == "call")
            game.apply(key, obs["version"])
            game.version += 1
    return {
        "review_status": "Pending Rayner review. No strategic approval or solver answer key.",
        "basis": "Legal scripted play for discussion; candidate labels are dormant heuristic hypotheses, not live model decisions.",
        "cases": cases,
    }


def render_markdown(pack):
    lines = [
        "# Stage 1 hand review",
        "",
        pack["review_status"],
        "",
        pack["basis"],
        "",
        "These are nine decisions from three legally played first hands. Hero is seat 0 (Player 1). The first two hands use scripted check/call play so every street can be reviewed; the third uses legal maximum raises by opponents. These scripts are discussion setups, not realistic-opponent claims.",
        "",
        "All cards below belong to hero or the public board. The complete permitted observations, evidence IDs, legal menus and dormant candidate hypotheses are in [the JSON pack](stage-1-hands.json). No opponent cards, deck seeds or scenario labels enter those observations.",
        "",
        "Recreate both review files from the repository root with `apps/api/.venv/bin/python scripts/stage1_review_pack.py`. The controller-only recipe is in that script. Byte-identical regeneration is checked. Do not pass the generator or experiment manifests to a playing agent.",
        "",
        "There is no solver answer key. Equity assumes uniform random opponent hands; pot odds omit side-pot eligibility and hand-start ICM is descriptive. Candidate intent labels do not select an action, and this module remains disconnected from live play.",
    ]
    for case in pack["cases"]:
        o = case["observation"]
        lines += [
            "",
            f"## {case['case_id']}: {o['street']}",
            "",
            f"Hero: {' '.join(o['hole'])}, {o['position']}. Board: {' '.join(o['board']) or 'None'}. Pot: {o['pot']} chips. To call: {o['to_call']} chips. Big blind: {o['big_blind']} chips.",
            "",
            "Legal choices: " + ", ".join(a["key"] for a in o["legal"]) + ".",
            "",
            "Public action sequence:",
            "",
        ]
        lines += [f"- {e['id']} ({e['street']}): {e['text']}" for e in o["history"]]
        lines += ["", "Discussion:", ""] + ["- " + q for q in case["discussion_points"]]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    result = build_pack()
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    (ROOT / "docs/review/stage-1-hands.json").write_text(encoded)
    (ROOT / "docs/review/stage-1-hands.md").write_text(render_markdown(result))
    print(
        f"{len(result['cases'])} cases; sha256={hashlib.sha256(encoded.encode()).hexdigest()}"
    )
