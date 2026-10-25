import argparse
import json
from pathlib import Path

from .manifest import Manifest, expand
from .runner import evaluate


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Offline validation by default. Explicit mock or live execution through shared table policies."
    )
    parser.add_argument("manifest", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--mock", action="store_true")
    mode.add_argument(
        "--live",
        action="store_true",
        help="Makes billable OpenRouter requests; requires explicit operator authorization",
    )
    parser.add_argument(
        "--mock-failure", choices=["http", "invalid", "timeout", "missing_usage"]
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        manifest = Manifest.model_validate_json(args.manifest.read_text())
        if args.mock_failure and not args.mock:
            raise ValueError("--mock-failure requires --mock")
        if not (args.mock or args.live):
            value = {"validated": True, "provider_calls": 0, "runs": expand(manifest)}
        else:
            if args.output is None:
                raise ValueError("Execution requires --output to preserve every result")
            if args.output.exists():
                raise ValueError("Output already exists; choose a new report path")
            value = evaluate(manifest, mock=args.mock, failure=args.mock_failure)
        if args.output:
            if args.output.exists():
                raise ValueError("Output already exists; choose a new report path")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(value, indent=2) + "\n")
            print(args.output)
        else:
            print(json.dumps(value, indent=2))
        return int(any(r["status"] != "completed" for r in value.get("results", [])))
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
