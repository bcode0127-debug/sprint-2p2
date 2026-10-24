"""Descriptive recalibration on the replication games (Amendment 1, section 2).

Per view, t and q are refit on replication trials 0 to 9 with the same fitting function that
scripts/fit_thresholds.py uses (sprint2p2.analysis.fit_all) and applied to trials 10 to 19 with seed
2026. Recall and the achieved FPR on trials 10 to 19 are reported under the frozen and the refit
thresholds. Run from the project root:
    PYTHONPATH=src .venv/bin/python -m scripts.recalibrate_replication
Refused until configs/frozen.json holds amendment1_url. No test is run.
"""

import argparse
import json
from pathlib import Path

from scripts import analyze as base
from scripts._scores import SCORES, load_dir
from sprint2p2 import analysis, metrics, splits, views

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "results" / "tables" / "replication" / "recalibration.json"
FIT_TRIALS = range(10)
APPLY_TRIALS = range(10, 20)

Rows = dict[str, dict]


def subset(rows: Rows, trials: range) -> Rows:
    """Keep the score rows whose trial is in the range."""
    return {i: r for i, r in rows.items() if r["trial"] in trials}


def applied(rows: Rows, fit: dict) -> dict:
    """Recall and achieved FPR of one fit on one set of rows (seed 2026)."""
    ids = sorted(rows)
    scores, _ = analysis.arrays(rows, ids)
    labels, _ = analysis.labels_games(rows, ids)
    res = metrics.apply_threshold(scores, labels, ids, fit)
    return {k: res[k] for k in ("recall", "fpr", "recall_expected", "fpr_expected")}


def recalibrate(rows_by_view: dict[str, Rows], frozen_fits: dict[str, dict]) -> dict:
    """Compare frozen and refit thresholds on trials 10 to 19, per view."""
    out = {}
    for view in views.VIEWS:
        rows = rows_by_view[view]
        refit = analysis.fit_all({view: subset(rows, FIT_TRIALS)})[view]
        held = subset(rows, APPLY_TRIALS)
        out[view] = {
            "frozen_fit": frozen_fits[view],
            "refit_on_trials_0_to_9": refit,
            "trials_10_to_19": {
                "n": len(held),
                "frozen": applied(held, frozen_fits[view]),
                "refit": applied(held, refit),
            },
        }
    return out


def main(argv: list[str] | None = None) -> None:
    """Command-line entry point."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args(argv)
    splits.check_gate("replication")
    fits = base.frozen_fits(base.require_frozen())
    result = {
        "tag": "descriptive, no test",
        "views": recalibrate(load_dir(SCORES / "replication"), fits),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
