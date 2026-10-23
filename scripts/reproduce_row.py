"""Recompute the primary row from committed score files, with no API calls.

Run from the project root with: PYTHONPATH=src .venv/bin/python -m scripts.reproduce_row
Uses the frozen thresholds when configs/frozen.json holds them; otherwise development data.
"""

import argparse

from scripts._scores import pick
from sprint2p2 import analysis


def main() -> None:
    """Print the primary row and its SHA-256."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev-only", action="store_true")
    args = ap.parse_args()
    thr, tst, tag = pick(dev_only=args.dev_only)
    text = analysis.canonical(analysis.primary_only(tst, tag, analysis.fit_all(thr)))
    print(text)  # noqa: T201
    print(f"sha256: {analysis.sha256(text)}")  # noqa: T201


if __name__ == "__main__":
    main()
