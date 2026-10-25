import argparse
from datetime import datetime, timezone
from pathlib import Path

from . import POLICIES, EvaluationConfig, PolicySpec, evaluate, save_report
from .policies import SCENARIOS


def seeds(value):
    try:
        return tuple(int(s) for s in value.split(",")) if value else ()
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Seeds must be comma-separated integers") from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description="Seeded local tournament evaluation (two tournaments by default).")
    parser.add_argument("--tuning-seeds", type=seeds, default=(1,))
    parser.add_argument("--held-out-seeds", type=seeds, default=(101,))
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--policy", choices=POLICIES, action="append")
    parser.add_argument("--adapter", help="Trusted local module:factory accepting seed and returning a policy")
    parser.add_argument("--policy-name")
    parser.add_argument("--policy-version")
    parser.add_argument("--scenario", choices=SCENARIOS, action="append")
    parser.add_argument("--opponent-profiles", default="tight,caller,aggressive,balanced,volatile")
    parser.add_argument("--stack-bb", type=int, default=10)
    parser.add_argument("--hands-per-level", type=int, default=2)
    parser.add_argument("--payouts", choices=("70/30", "winner-take-all"), default="70/30")
    parser.add_argument("--max-hands", type=int, default=300)
    parser.add_argument("--max-actions", type=int, default=5000)
    parser.add_argument("--timeout-seconds", type=float, default=120)
    parser.add_argument("--output", type=Path, default=Path("data/evaluation") / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    args = parser.parse_args(argv)
    if args.adapter and not (args.policy_name and args.policy_version):
        parser.error("--adapter requires --policy-name and --policy-version")
    if not args.adapter and (args.policy_name or args.policy_version):
        parser.error("--policy-name and --policy-version require --adapter")
    if args.output.exists():
        parser.error("Output directory already exists; choose a new directory")
    try:
        policies = tuple(POLICIES[n] for n in (args.policy or ([] if args.adapter else ["heuristic"])))
        if args.adapter:
            policies += (PolicySpec(args.policy_name, args.policy_version, args.adapter),)
        config = EvaluationConfig(
            tuning_seeds=args.tuning_seeds, held_out_seeds=args.held_out_seeds,
            repeats=args.repeats, policies=policies, scenarios=tuple(args.scenario or ["standard"]),
            opponent_profiles=tuple(args.opponent_profiles.split(",")), stack_bb=args.stack_bb,
            hands_per_level=args.hands_per_level, payouts=args.payouts,
            max_hands=args.max_hands, max_actions=args.max_actions, timeout_seconds=args.timeout_seconds,
        )
    except ValueError as exc:
        parser.error(str(exc))
    report = evaluate(config)
    print(save_report(report, args.output), end="")
    print(f"Results: {args.output / 'results.json'}")
    return int(any(r["status"] != "completed" for r in report["results"]))


if __name__ == "__main__":
    raise SystemExit(main())
