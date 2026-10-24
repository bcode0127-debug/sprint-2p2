"""Test whether averaging the two both-view runs beats either run (DEV-ONLY, no API calls).

Run 1 is the v2 scores in results/dev_prompt_round.json; run 2 is the test-retest rerun cached at
~/apart-sprint/docs/run-logs/retest_run2.jsonl. Run from the project root with:
    PYTHONPATH=src .venv/bin/python -m scripts.average_runs_dev
"""

import json
from pathlib import Path

import numpy as np

from sprint2p2 import metrics, scoring, splits

ROOT = Path(__file__).resolve().parent.parent
RUN1 = ROOT / "results" / "dev_prompt_round.json"
RUN2 = Path.home() / "apart-sprint" / "docs" / "run-logs" / "retest_run2.jsonl"
OUT = ROOT / "results" / "dev_run_averaging.json"


def main() -> None:
    """Write results/dev_run_averaging.json."""
    cases = splits.split_cases(splits.load_logs(), "dev")
    ids = [scoring.case_id(c) for c in cases]
    one = {scoring.case_id(c): c["score_v2"] for c in json.loads(RUN1.read_text())["cases"]}
    two = scoring.read_rows(RUN2)
    if set(ids) - set(two) or any(one[i] is None or not two[i]["parse_ok"] for i in ids):
        msg = "run 1 or run 2 is missing scores for some development cases"
        raise SystemExit(msg)
    s1 = np.array([one[i] for i in ids], float)
    s2 = np.array([two[i]["score"] for i in ids], float)
    avg = (s1 + s2) / 2
    labels = np.array([c["label"] for c in cases], bool)
    games = [c["game"] for c in cases]
    result = {
        "tag": "DEV-ONLY",
        "n_cases": len(ids),
        "n_games": len(set(games)),
        "auroc": {
            "run1": metrics.auroc(s1, labels),
            "run2": metrics.auroc(s2, labels),
            "average": metrics.auroc(avg, labels),
        },
        "distinct_values": {
            "run1": len(np.unique(s1)),
            "run2": len(np.unique(s2)),
            "average": len(np.unique(avg)),
        },
        "average_minus_run1": metrics.paired_bootstrap(avg, s1, labels, games),
        "average_minus_run2": metrics.paired_bootstrap(avg, s2, labels, games),
        "spearman_run1_run2": metrics.spearman(s1, s2),
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
