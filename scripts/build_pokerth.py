"""Offline native build from verified vendored PokerTH source. No Qt required."""

import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "native/pokerth"


def main():
    manifest = json.loads((NATIVE / "upstream.json").read_text())
    for name, hashes in manifest["files"].items():
        data = (NATIVE / "vendor" / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != hashes["sha256"]:
            raise SystemExit(f"Vendored source checksum mismatch: {name}")
    output = NATIVE / "build"
    output.mkdir(exist_ok=True)
    sources = NATIVE / "vendor/src/engine/local_engine"
    compiler = shlex.split(os.environ.get("CXX", "c++"))
    with tempfile.TemporaryDirectory(dir=output) as temporary:
        binary = Path(temporary) / "pokerth-opponent"
        command = [
            *compiler,
            "-std=c++20",
            "-O2",
            "-Wall",
            "-Wextra",
            "-I",
            str(sources),
            "-I",
            str(NATIVE / "vendor/src"),
            str(NATIVE / "bridge.cpp"),
            *[
                str(sources / (name + ".cpp"))
                for name in (
                    "aiengine4",
                    "equitycalculator",
                    "holecardsrange",
                    "handevaluator",
                )
            ],
            "-o",
            str(binary),
        ]
        subprocess.run(command, check=True)
        subprocess.run([str(binary), "--version"], check=True)
        binary.replace(output / "pokerth-opponent")
    (output / "build.json").write_text(
        json.dumps(
            {
                "upstream": manifest["revision"],
                "compiler": subprocess.check_output(
                    [*compiler, "--version"], text=True
                ).splitlines()[0],
                "bridge_sha256": hashlib.sha256(
                    (NATIVE / "bridge.cpp").read_bytes()
                ).hexdigest(),
            },
            indent=2,
        )
        + "\n"
    )
    print(f"Built {output / 'pokerth-opponent'}")


if __name__ == "__main__":
    main()
