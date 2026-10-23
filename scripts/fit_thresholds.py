"""Fit per-scorer (t, q) on threshold-split scores and write them into configs/frozen.json.

Run from the project root, after the threshold split has been scored:
    PYTHONPATH=src .venv/bin/python -m scripts.fit_thresholds
"""

import argparse
import json
from pathlib import Path

from scripts._scores import load_dir
from sprint2p2 import analysis, splits

ROOT = Path(__file__).resolve().parent.parent
FPR_TARGET = 0.10


def fit_thresholds(frozen_path: Path, threshold_dir: Path) -> dict:
    """Fit every scorer on the threshold scores and update the freeze file in place."""
    if not frozen_path.exists():
        msg = f"{frozen_path.name} not found: freeze first"
        raise splits.GateError(msg)
    frozen = json.loads(frozen_path.read_text())
    splits.check_gate("threshold", frozen_path)
    rows = load_dir(threshold_dir)
    missing = [n for n in analysis.SCORERS if n not in rows]
    if missing:
        msg = f"no threshold-split scores for: {', '.join(missing)}"
        raise SystemExit(msg)
    fits = analysis.fit_all({n: rows[n] for n in analysis.SCORERS})
    frozen["thresholds"] = {
        n: {"t": f["t"], "q": f["q"], "fpr_target": FPR_TARGET} for n, f in fits.items()
    }
    frozen["threshold_scores_sha256"] = {
        n: analysis.sha256((threshold_dir / f"{n}.jsonl").read_text()) for n in analysis.SCORERS
    }
    frozen_path.write_text(json.dumps(frozen, indent=2, sort_keys=True) + "\n")
    return frozen


def main() -> None:
    """Fit and report which scorers were written."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--frozen", default=str(splits.FROZEN))
    ap.add_argument("--threshold-dir", default=str(ROOT / "scores" / "threshold"))
    args = ap.parse_args()
    frozen = fit_thresholds(Path(args.frozen), Path(args.threshold_dir))
    print(f"wrote thresholds for {len(frozen['thresholds'])} scorers")  # noqa: T201


if __name__ == "__main__":
    main()
