"""DEV-ONLY PRACTICE analysis of other monitor models against Haiku (exploration, not registered).

Run from the practice worktree root:
    PYTHONPATH=src ../sprint2p2/.venv/bin/python -m scripts.analyze_practice
Writes results/practice_monitors_dev.json and .md. Haiku's scores come from scores/dev (Both run 1)
and the test-retest run 2 cached at ~/apart-sprint/docs/run-logs/retest_run2.jsonl.
"""

import json
from itertools import combinations
from pathlib import Path

import numpy as np

from sprint2p2 import analysis, combine, metrics, pergame, scoring, splits
from sprint2p2.fishing_analysis import contrast

ROOT = Path(__file__).resolve().parent.parent
SCORES = ROOT / "scores"
RUN2 = Path.home() / "apart-sprint" / "docs" / "run-logs" / "retest_run2.jsonl"
OUT_JSON = ROOT / "results" / "practice_monitors_dev.json"
OUT_MD = ROOT / "results" / "practice_monitors_dev.md"
TAG = "DEV-ONLY PRACTICE"
PRICES = {  # OpenRouter list prices per token on 2026-10-24
    "haiku": (1e-7, 5e-7),
    "gemini": (8.25e-7, 4.125e-6),
    "sonnet": (2e-6, 1e-5),
}
MODEL_VIEWS = {
    "haiku": ("both", "actions_only", "messages_only"),
    "gemini": ("both", "actions_only", "messages_only"),
    "sonnet": ("both", "actions_only"),
}
DIRS = {
    "haiku": SCORES / "dev",
    "gemini": SCORES / "practice_gemini_dev",
    "sonnet": SCORES / "practice_sonnet_dev",
}

Rows = dict[str, dict]


def rank_average_block(
    a: np.ndarray,
    b: np.ndarray,
    labels: np.ndarray,
    games: list[str],
    n_boot: int = metrics.N_BOOT,
) -> dict:
    """AUROC of the rank average of two scorers and its differences from each part."""
    boot = combine.combo_bootstrap(a, b, labels, games, n_boot=n_boot)

    def part(entry: dict) -> dict:
        keys = ("diff", "mean_of_per_game_differences", "lower_95_one_sided", "p_one_sided")
        return {k: entry[k] for k in keys}

    return {
        "average_auroc": boot["combo_auroc"],
        "part_a_auroc": boot["both_auroc"],
        "part_b_auroc": boot["counting_auroc"],
        "minus_a": part(boot["C1"]),
        "minus_b": part(boot["C2"]),
    }


def tokens_and_cost(rows_by_view: dict[str, Rows], model: str) -> dict:
    """Totals across a model's rows: parse failures, tokens, estimated cost and model ids."""
    rows = [r for view in rows_by_view.values() for r in view.values()]
    prompt = sum(r.get("prompt_tokens", 0) for r in rows)
    completion = sum(r.get("completion_tokens", 0) for r in rows)
    price_p, price_c = PRICES[model]
    return {
        "calls": len(rows),
        "parse_failures": sum(not r["parse_ok"] for r in rows),
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "reasoning_tokens": sum(r.get("reasoning_tokens", 0) for r in rows),
        "estimated_cost_usd": prompt * price_p + completion * price_c,
        "returned_models": sorted({m for r in rows for m in r.get("models", [])}),
    }


def load_models() -> tuple[dict[str, dict[str, Rows]], Rows]:
    """Load every model's score rows and Haiku's counting-rule rows."""
    rows = {
        m: {v: scoring.read_rows(DIRS[m] / f"{v}.jsonl") for v in views}
        for m, views in MODEL_VIEWS.items()
    }
    return rows, scoring.read_rows(DIRS["haiku"] / "counting.jsonl")


def main() -> None:
    """Compute and write the DEV-ONLY PRACTICE results."""
    cases = splits.split_cases(splits.load_logs(), "dev")
    ids = sorted(scoring.case_id(c) for c in cases)
    rows, counting_rows = load_models()
    run2 = scoring.read_rows(RUN2)
    first = rows["haiku"]["both"]
    labels, games = analysis.labels_games(first, ids)
    arr = {
        m: {v: analysis.arrays(r, ids)[0] for v, r in views.items()} for m, views in rows.items()
    }
    arr["haiku"]["both_run2"] = analysis.arrays(run2, ids)[0]
    counting = analysis.arrays(counting_rows, ids)[0]
    both = {m: arr[m]["both"] for m in MODEL_VIEWS}
    result = {
        "tag": TAG,
        "note": "exploration for future work; nothing here is a registered result",
        "n_cases": len(ids),
        "n_games": len(set(games)),
        "auroc": {
            m: {
                v: {"auroc": metrics.auroc(s, labels), "ci95": metrics.auroc_ci(s, labels, games)}
                for v, s in views.items()
            }
            for m, views in arr.items()
        },
        "announcement_gain_both_minus_actions_only": {
            m: contrast(arr[m]["both"], arr[m]["actions_only"], labels, games) for m in MODEL_VIEWS
        },
        "both_minus_haiku_both": {
            m: {
                run: contrast(both[m], arr["haiku"][key], labels, games)
                for run, key in (("run1", "both"), ("run2", "both_run2"))
            }
            for m in ("gemini", "sonnet")
        },
        "spearman_on_both": {
            f"{a}_{b}": metrics.spearman(both[a], both[b]) for a, b in combinations(MODEL_VIEWS, 2)
        },
        "rank_averages_on_both": {
            f"{a}+{b}": rank_average_block(both[a], both[b], labels, games)
            for a, b in combinations(MODEL_VIEWS, 2)
        },
        "with_counting_rule": {
            m: rank_average_block(both[m], counting, labels, games) for m in MODEL_VIEWS
        },
        "counting_auroc": metrics.auroc(counting, labels),
        "usage": {m: tokens_and_cost(rows[m], m) for m in MODEL_VIEWS},
    }
    result["per_game_check"] = pergame.per_game_auroc_difference(
        both["sonnet"], both["gemini"], labels, games
    )["mean_of_per_game_differences"]
    OUT_JSON.write_text(json.dumps(result, indent=2) + "\n")
    OUT_MD.write_text(render(result))


def fmt(x: float | None) -> str:
    """Format a number for markdown."""
    return "n/a" if x is None else f"{x:.3f}"


def render(res: dict) -> str:
    """Render the short DEV-ONLY PRACTICE markdown report."""
    lines = [
        (
            f"**{res['tag']}**: exploration for future work; not a registered result. "
            f"{res['n_cases']} development cases, {res['n_games']} games.\n"
        ),
        "## AUROC (95% game-bootstrap interval)\n",
        "| model | view | AUROC | 95% CI |",
        "|---|---|---|---|",
    ]
    for m, views in res["auroc"].items():
        for v, e in views.items():
            lines.append(
                f"| {m} | {v} | {fmt(e['auroc'])} | {fmt(e['ci95'][0])} to {fmt(e['ci95'][1])} |"
            )
    lines += [
        "\n## Announcement gain (Both minus Actions-only)\n",
        "| model | pooled | per-game mean | one-sided 5th pct | two-sided 95% |",
        "|---|---|---|---|---|",
    ]
    for m, e in res["announcement_gain_both_minus_actions_only"].items():
        ci = e["descriptive_two_sided_ci95"]
        lines.append(
            f"| {m} | {fmt(e['diff'])} | {fmt(e['mean_of_per_game_differences'])} | "
            f"{fmt(e['lower_95_one_sided'])} | {fmt(ci[0])} to {fmt(ci[1])} |",
        )
    lines += [
        "\n## New model Both minus Haiku Both\n",
        "| model | vs | pooled | per-game mean | two-sided 95% |",
        "|---|---|---|---|---|",
    ]
    for m, runs in res["both_minus_haiku_both"].items():
        for run, e in runs.items():
            ci = e["descriptive_two_sided_ci95"]
            lines.append(
                f"| {m} | haiku {run} | {fmt(e['diff'])} | "
                f"{fmt(e['mean_of_per_game_differences'])} | "
                f"{fmt(ci[0])} to {fmt(ci[1])} |",
            )
    lines += ["\n## Spearman on Both\n"] + [
        f"- {k}: {fmt(v)}" for k, v in res["spearman_on_both"].items()
    ]
    lines += [
        "\n## Rank averages on Both\n",
        "| pair | AUROC | part a | part b | minus a | minus b |",
        "|---|---|---|---|---|---|",
    ]
    for k, e in res["rank_averages_on_both"].items():
        lines.append(
            f"| {k} | {fmt(e['average_auroc'])} | {fmt(e['part_a_auroc'])} | "
            f"{fmt(e['part_b_auroc'])} | "
            f"{fmt(e['minus_a']['diff'])} | {fmt(e['minus_b']['diff'])} |",
        )
    lines.append(
        "\n## Both rank-averaged with the counting rule "
        f"(counting alone {fmt(res['counting_auroc'])})\n",
    )
    lines += [
        "| model | AUROC | Both alone | minus Both | minus counting |",
        "|---|---|---|---|---|",
    ]
    for m, e in res["with_counting_rule"].items():
        lines.append(
            f"| {m} | {fmt(e['average_auroc'])} | {fmt(e['part_a_auroc'])} | "
            f"{fmt(e['minus_a']['diff'])} | {fmt(e['minus_b']['diff'])} |",
        )
    lines += [
        "\n## Usage\n",
        "| model | calls | parse failures | prompt | completion | reasoning | est. cost USD |",
        "|---|---|---|---|---|---|---|",
    ]
    for m, u in res["usage"].items():
        lines.append(
            f"| {m} | {u['calls']} | {u['parse_failures']} | {u['prompt_tokens']} | "
            f"{u['completion_tokens']} | {u['reasoning_tokens']} | {u['estimated_cost_usd']:.3f} |",
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
