"""Score the Fishing development pilot (DEV-ONLY, rounds 1 to 9) on both and actions_only.

Run from the project root with: PYTHONPATH=src .venv/bin/python -m scripts.fishing_pilot_dev
Uses the locked v2 monitor settings with the Fishing prompt. Nothing here is a test result.
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from scripts.score_views import CONFIG, read_key
from sprint2p2 import budget, fishing, metrics, monitor, scoring, splits

ROOT = Path(__file__).resolve().parent.parent
SCORES = ROOT / "scores" / "fishing_dev"
OUT_JSON = ROOT / "results" / "fishing_pilot_dev.json"
OUT_MD = ROOT / "results" / "fishing_pilot_dev.md"
VIEWS = ("both", "actions_only")
PRICE_PROMPT = 1e-7
PRICE_COMPLETION = 5e-7
TAG = "DEV-ONLY"


def per_game_auroc(scores: np.ndarray, labels: np.ndarray, games: list[str]) -> dict:
    """Return the AUROC inside each game (None where one class is missing)."""
    arr = np.asarray(games)
    return {g: metrics.auroc(scores[arr == g], labels[arr == g]) for g in sorted(set(games))}


def block(scores: np.ndarray, labels_a: np.ndarray, labels_b: np.ndarray, games: list[str]) -> dict:
    """AUROC under both labels, with a game-clustered interval on label (a)."""
    return {
        "auroc_a": metrics.auroc(scores, labels_a),
        "auroc_a_ci95": metrics.auroc_ci(scores, labels_a, games),
        "auroc_b": metrics.auroc(scores, labels_b),
        "per_game_auroc_a": per_game_auroc(scores, labels_a, games),
    }


def score_views(cases: list[dict], runner: scoring.Runner, workers: int) -> dict[str, list[dict]]:
    """Score each view over all cases and save the rows."""
    rows = {}
    for view in VIEWS:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            rows[view] = list(pool.map(lambda c, v=view: fishing.score_case(c, v, runner), cases))
        scoring.write_rows(SCORES / f"{view}.jsonl", rows[view])
    return rows


def rates(labels_a: np.ndarray, labels_b: np.ndarray) -> dict:
    """Break rates under (a) and (b), keep counts and the over/under split."""
    n = len(labels_a)
    over, under = int(labels_b.sum()), int((labels_a & ~labels_b).sum())
    return {
        "n_cases": n,
        "break_rate_a_any_change": float(labels_a.mean()),
        "break_rate_b_over_take_only": float(labels_b.mean()),
        "keeps_a": int((~labels_a).sum()),
        "keeps_b": int((~labels_b).sum()),
        "over_take": over,
        "under_take": under,
        "unchanged": int((~labels_a).sum()),
    }


def markdown(result: dict) -> str:
    """Render the short DEV-ONLY report."""
    lines = [
        f"**{TAG}**: Fishing development pilot, rounds 1 to 9, 3 games. Not a test result.\n",
        "| scorer | AUROC (a) | 95% CI (3 games) | AUROC (b) |",
        "|---|---|---|---|",
    ]
    for name, b in result["scorers"].items():
        ci = f"{b['auroc_a_ci95'][0]:.3f} to {b['auroc_a_ci95'][1]:.3f}"
        lines.append(f"| {name} | {b['auroc_a']:.3f} | {ci} | {b['auroc_b']:.3f} |")
    c = result["contrast_both_minus_actions_only"]
    lines += [
        "",
        (
            f"both - actions_only (label a): diff {c['diff']:.3f}, one-sided 5th percentile "
            f"{c['lower_95_one_sided']:.3f}, between-game SD {c['between_game_sd']:.3f}"
        ),
        "",
        (
            f"Break rate (a) {result['rates']['break_rate_a_any_change']:.3f}, "
            f"(b) {result['rates']['break_rate_b_over_take_only']:.3f}; "
            f"over-take {result['rates']['over_take']}, "
            f"under-take {result['rates']['under_take']}, "
            f"unchanged {result['rates']['unchanged']}"
        ),
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    """Run the pilot and write results/fishing_pilot_dev.json and .md."""
    started = time.time()
    log = json.loads(splits.FISHING_PILOT_RAW.read_text())
    cases = fishing.fishing_cases(log, "fishpilot")
    cfg = monitor.load_config(CONFIG)
    if cfg != monitor.VARIANTS["v2"]:
        msg = "configs/monitor.json is not the locked v2 setting"
        raise SystemExit(msg)
    key = read_key()
    usage_before = budget.get_usage(key)
    budget.check_budget(usage_before, len(cases) * len(VIEWS))
    workers = json.loads(CONFIG.read_text())["concurrency"]
    runner = scoring.Runner({"fishpilot": log}, cfg, monitor.make_post(key))
    rows = score_views(cases, runner, workers)
    la = np.array([c["label"] for c in cases], bool)
    lb = np.array([c["label_over"] for c in cases], bool)
    games = [c["game"] for c in cases]
    scores = {
        v: np.array([r["score"] if r["parse_ok"] else -1.0 for r in rs], float)
        for v, rs in rows.items()
    }
    rule_vals = [fishing.rule_scores(log, c["trial"], c["round"], c["agent"]) for c in cases]
    for name in fishing.RULE_NAMES:
        scores[name] = np.array([v[name] for v in rule_vals], float)
    boot = metrics.paired_bootstrap(scores["both"], scores["actions_only"], la, games)
    pg_b, pg_a = (per_game_auroc(scores[v], la, games) for v in ("both", "actions_only"))
    diffs = [pg_b[g] - pg_a[g] for g in pg_b if pg_b[g] is not None and pg_a[g] is not None]
    tokens = {
        v: {k: sum(r[f"{k}_tokens"] for r in rs) for k in ("prompt", "completion", "reasoning")}
        for v, rs in rows.items()
    }
    cost = sum(
        t["prompt"] * PRICE_PROMPT + t["completion"] * PRICE_COMPLETION for t in tokens.values()
    )
    result = {
        "tag": TAG,
        "n_games": len(set(games)),
        "rates": rates(la, lb),
        "scorers": {n: block(s, la, lb, games) for n, s in scores.items()},
        "contrast_both_minus_actions_only": {
            **boot,
            "per_game_differences": diffs,
            "between_game_sd": float(np.std(diffs, ddof=1)) if len(diffs) > 1 else None,
        },
        "parse_failures": {v: sum(not r["parse_ok"] for r in rs) for v, rs in rows.items()},
        "tokens": tokens,
        "estimated_cost_usd": cost,
        "usage_before": usage_before,
        "usage_after": budget.get_usage(key),
        "run_time_seconds": time.time() - started,
        "monitor_config": "configs/monitor.json (v2) with prompts/monitor_prompt_fishing_v1.txt",
    }
    OUT_JSON.write_text(json.dumps(result, indent=2) + "\n")
    OUT_MD.write_text(markdown(result))


if __name__ == "__main__":
    main()
