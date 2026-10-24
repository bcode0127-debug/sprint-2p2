"""AUROC of the Both view for each harness break type against all keeps (no API calls).

    PYTHONPATH=src .venv/bin/python -m scripts.break_type_auroc

For the test and replication splits, the cases of one break type (typology from the raw log, as
in scripts.analyze.build_meta) are the positives and every keep is a negative; ties count 0.5.
Writes results/tables/break_type_auroc.json. Descriptive; no test is run.
"""

import json
from pathlib import Path

import numpy as np

from scripts import analyze as base
from scripts._scores import SCORES, load_dir
from sprint2p2 import analysis, metrics, splits

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "results" / "tables" / "break_type_auroc.json"
SPLITS = ("test", "replication")
VIEW = "both"
BREAK_TYPES = analysis.BREAK_TYPES


def by_type(rows: dict[str, dict], typology: dict[str, str]) -> dict:
    """n, keeps and AUROC of each break type against all keeps, for one view's score rows."""
    ids = sorted(rows)
    scores, _ = analysis.arrays(rows, ids)
    labels, _ = analysis.labels_games(rows, ids)
    kinds = np.array([typology.get(i, "other") for i in ids])
    keep = ~labels
    out = {}
    for kind in BREAK_TYPES:
        pick = (kinds == kind) & labels
        use = pick | keep
        out[kind] = {
            "n": int(pick.sum()),
            "n_keep": int(keep.sum()),
            "auroc": metrics.auroc(scores[use], pick[use]),
        }
    return out


def build() -> dict:
    """Compute the table for every split from the committed score files and raw logs."""
    logs = splits.load_logs()
    result = {
        "tag": "descriptive, no test",
        "view": VIEW,
        "note": "AUROC of each break type against all keeps; ties count 0.5",
    }
    for split in SPLITS:
        splits.check_gate(split)
        rows = load_dir(SCORES / split)[VIEW]
        typology = base.build_meta(logs, split, SCORES / split)["typology"]
        result[split] = by_type(rows, typology)
    return result


def main() -> None:
    """Write the JSON file."""
    DEFAULT_OUT.write_text(json.dumps(build(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
