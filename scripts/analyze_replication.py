"""Run the registered analysis on the El Farol replication split (Amendment 1, section 2).

This wrapper calls scripts/analyze.py's require_frozen, frozen_fits, build_meta and render, and
sprint2p2.analysis.analyze, unchanged, on a different evaluated set. Run from the project root:
    PYTHONPATH=src .venv/bin/python -m scripts.analyze_replication [--split replication]
The replication split is refused until configs/frozen.json holds amendment1_url. Pointed at the
test split it reproduces results/tables/final exactly (a test checks this).
"""

import argparse
from pathlib import Path

from scripts import analyze as base
from scripts._scores import SCORES, load_dir
from sprint2p2 import analysis, splits

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "results" / "tables" / "replication"


def run(split: str, out: Path) -> Path:
    """Evaluate the split with the frozen fits and write tables.json and tables.md to out."""
    splits.check_gate(split)
    fits = base.frozen_fits(base.require_frozen())
    thr = load_dir(SCORES / "threshold")
    tst = load_dir(SCORES / split)
    meta = base.build_meta(splits.load_logs(), split, SCORES / split)
    tables = analysis.analyze(thr, tst, "", fits, meta)
    out.mkdir(parents=True, exist_ok=True)
    (out / "tables.json").write_text(analysis.canonical(tables) + "\n")
    (out / "tables.md").write_text(base.render(tables))
    return out


def main(argv: list[str] | None = None) -> None:
    """Command-line entry point."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="replication", choices=["replication", "test"])
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args(argv)
    run(args.split, Path(args.out))


if __name__ == "__main__":
    main()
