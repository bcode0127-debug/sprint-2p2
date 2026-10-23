"""DEV-ONLY test-retest of the locked monitor on the 585 development cases (both view).

Run 1 is the v2 scores in results/dev_prompt_round.json; run 2 is a fresh scoring pass.
Run from the project root with: PYTHONPATH=src .venv/bin/python -m scripts.test_retest_dev
"""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from scripts.score_views import CONFIG, read_key
from sprint2p2 import metrics, monitor, scoring, splits

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path.home() / "apart-sprint" / "docs" / "run-logs" / "retest_run2.jsonl"
RUN1 = ROOT / "results" / "dev_prompt_round.json"
OUT = ROOT / "results" / "test_retest_dev.json"
PRICE_PROMPT = 1e-7
PRICE_COMPLETION = 5e-7
EXPECTED_CASES = 585


def run1_scores() -> dict[str, int | None]:
    """Read run-1 v2 scores keyed by case id."""
    cases = json.loads(RUN1.read_text())["cases"]
    return {scoring.case_id(c): c["score_v2"] for c in cases}


def run2_rows(cases: list[dict], logs: dict) -> list[dict]:
    """Score all cases again with the locked config, caching rows on disk."""
    if CACHE.exists():
        return [json.loads(line) for line in CACHE.read_text().splitlines() if line]
    cfg = monitor.load_config(CONFIG)
    if cfg != monitor.VARIANTS["v2"]:
        msg = "configs/monitor.json is not the v2 setting"
        raise SystemExit(msg)
    runner = scoring.Runner(logs, cfg, monitor.make_post(read_key()))
    workers = json.loads(CONFIG.read_text())["concurrency"]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(lambda c: scoring.score_case(c, "both", runner), cases))
    scoring.write_rows(CACHE, rows)
    return rows


def main() -> None:
    """Compute and write results/test_retest_dev.json."""
    logs = splits.load_logs()
    cases = splits.split_cases(logs, "dev")
    if len(cases) != EXPECTED_CASES:
        msg = f"expected {EXPECTED_CASES} dev cases, got {len(cases)}"
        raise SystemExit(msg)
    rows = run2_rows(cases, logs)
    one = run1_scores()
    ids = [scoring.case_id(c) for c in cases]
    labels = np.array([c["label"] for c in cases], dtype=bool)
    games = [c["game"] for c in cases]
    s1 = np.array([one[i] if one[i] is not None else analysis_missing() for i in ids], float)
    s2 = np.array(
        [
            r["score"] if r["parse_ok"] and r["score"] is not None else analysis_missing()
            for r in rows
        ],
        float,
    )
    both_ok = np.array(
        [one[i] is not None and r["parse_ok"] for i, r in zip(ids, rows, strict=True)]
    )
    fit = metrics.randomized_threshold(s1, labels)
    app1 = metrics.apply_threshold(s1, labels, ids, fit)
    app2 = metrics.apply_threshold(s2, labels, ids, fit)
    a1, a2 = metrics.auroc(s1, labels), metrics.auroc(s2, labels)
    prompt = sum(r["prompt_tokens"] for r in rows)
    completion = sum(r["completion_tokens"] for r in rows)
    result = {
        "tag": "DEV-ONLY",
        "n_cases": len(cases),
        "n_games": len(set(games)),
        "view": "both",
        "config": "configs/monitor.json (v2: prompt v1, reasoning 1024, no temperature)",
        "spearman_run1_run2": metrics.spearman(s1[both_ok], s2[both_ok]),
        "n_pairs_both_parsed": int(both_ok.sum()),
        "exact_agreement_share": float(np.mean(s1[both_ok] == s2[both_ok])),
        "mean_abs_score_difference": float(np.mean(np.abs(s1[both_ok] - s2[both_ok]))),
        "auroc": {"run1": a1, "run2": a2, "change_run2_minus_run1": a2 - a1},
        "auroc_change_bootstrap": metrics.paired_bootstrap(s2, s1, labels, games),
        "threshold_fit_on_run1": fit,
        "threshold_applied_unchanged": {"run1": app1, "run2": app2},
        "parse_failures": {
            "run1": sum(v is None for v in one.values()),
            "run2": sum(not r["parse_ok"] for r in rows),
        },
        "run2_tokens": {
            "prompt": prompt,
            "completion": completion,
            "reasoning": sum(r["reasoning_tokens"] for r in rows),
        },
        "run2_estimated_cost_usd": prompt * PRICE_PROMPT + completion * PRICE_COMPLETION,
        "run2_returned_models": sorted({m for r in rows for m in r["models"]}),
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")


def analysis_missing() -> float:
    """Return the score given to a parse failure."""
    from sprint2p2 import analysis  # noqa: PLC0415

    return analysis.MISSING


if __name__ == "__main__":
    main()
