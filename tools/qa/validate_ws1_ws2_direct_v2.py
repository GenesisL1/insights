#!/usr/bin/env python3
"""Stricter acceptance wrapper for the corrected direct-ID audit."""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--molnft", required=True, type=pathlib.Path)
    parser.add_argument("--network", required=True, type=pathlib.Path)
    args = parser.parse_args()

    subprocess.run(
        [
            sys.executable,
            "tools/qa/validate_ws1_ws2_direct.py",
            "--molnft",
            str(args.molnft),
            "--network",
            str(args.network),
        ],
        check=True,
    )
    summary = json.loads((args.molnft / "summary.json").read_text(encoding="utf-8"))
    n = int(summary["N"])
    successes = int(summary["successes"])
    failures = int(summary["failures"])
    fidelity = int(summary["fidelity_passes"])
    if successes <= 0:
        raise SystemExit("the randomized audit produced no successful fidelity comparison")
    if successes + failures != n:
        raise SystemExit("success and failure counts do not reconcile to N")
    if fidelity != successes:
        raise SystemExit("every SUCCESS row must be a declared canonical-fidelity pass")
    print(f"Corrected direct-ID acceptance passed: {successes}/{n} fidelity passes; {failures} failures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
