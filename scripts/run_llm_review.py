"""Save offline engineering evidence. All provider transports are explicit mocks."""

import argparse
import json
import statistics
from copy import deepcopy
from pathlib import Path

from wtr.llmbench import evaluate
from wtr.llmbench.manifest import digest


def compact(report):
    result = {k: v for k, v in report.items() if k != "results"}
    result["review_format"] = (
        "Compact derivative. Reconstruct each resolved configuration with expand(manifest); full action/usage records remain in the full report."
    )
    result["player_versions_by_preset"] = {
        r["preset"]: r["player_versions"] for r in report["results"]
    }
    result["results"] = []
    for row in report["results"]:
        summary = {
            k: v
            for k, v in row.items()
            if k
            not in (
                "accepted_actions",
                "chat",
                "latency_ms",
                "config",
                "stopping",
                "player_versions",
                "usage",
            )
        }
        summary.update(
            config_sha256=digest(row["config"]),
            hero_seat=row["config"]["hero_seat"],
            usage_total=row["usage"]["total"],
            attempts_by_player={
                p: u["attempts"] for p, u in row["usage"]["by_player"].items()
            },
            fallbacks_by_player={
                p: u["fallbacks"] for p, u in row["usage"]["by_player"].items()
            },
            accepted_actions_sha256=digest(row["accepted_actions"]),
            chat_sha256=digest(row["chat"]),
            chat_messages=len(row["chat"]),
            accepted_actions_legal=all(
                a["action"] in a["legal_keys"] for a in row["accepted_actions"]
            ),
            mean_latency_ms=statistics.mean(row["latency_ms"])
            if row["latency_ms"]
            else None,
            max_latency_ms=max(row["latency_ms"]) if row["latency_ms"] else None,
        )
        result["results"].append(summary)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "benchmarks/llm-smoke.json").read_text())

    def write(name, value):
        (args.output / name).write_text(json.dumps(value, indent=2) + "\n")

    report = evaluate(manifest, mock=True)
    write("benchmark-full.json", report)
    write("benchmark-review.json", compact(report))
    write(
        "sample-game.json",
        {
            "mocked": True,
            "source_sha256": report["source_sha256"],
            "purpose": report["purpose"],
            "game": report["results"][0],
        },
    )
    small = deepcopy(manifest)
    small.update(seeds=small["seeds"][:1], rotations=[0], presets=["same_model"])
    failures = []
    for scenario in (
        "http",
        "invalid",
        "timeout",
        "missing_usage",
        "budget",
        "run_timeout",
    ):
        config = deepcopy(small)
        config["table"]["llm_limits"] = {"deadline_seconds": 0.05}
        if scenario == "budget":
            config["table"]["llm_limits"]["max_calls_total"] = 1
        if scenario == "run_timeout":
            config["table"]["llm_limits"]["deadline_seconds"] = 10
            config["stopping"]["timeout_seconds"] = 0.1
        fault = (
            None
            if scenario == "budget"
            else "timeout"
            if scenario == "run_timeout"
            else scenario
        )
        report = evaluate(config, mock=True, failure=fault)
        report["review_scenario"] = scenario
        failures.append(report)
    write("failures-full.json", failures)
    write("failures-review.json", [compact(r) for r in failures])
    print(args.output)


if __name__ == "__main__":
    main()
