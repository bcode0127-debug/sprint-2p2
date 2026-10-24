"""Fishing transfer analysis (Amendment 1, section 4).

    PYTHONPATH=src .venv/bin/python -m scripts.analyze_fishing [--dev-only]

Real mode needs configs/frozen.json with amendment1_url, both batch logs and scores/fishing_test.
--dev-only uses scores/fishing_dev, labels everything DEV-ONLY and writes only to
results/tables/DEV-ONLY-fishing/.
"""

import argparse
import json
from pathlib import Path

from scripts import analyze as base
from scripts._scores import SCORES, load_dir
from sprint2p2 import analysis, fishing, fishing_analysis, scoring, splits

ROOT = Path(__file__).resolve().parent.parent
DEV_OUT = ROOT / "results" / "tables" / "DEV-ONLY-fishing"
TEST_OUT = ROOT / "results" / "tables" / "fishing_test"
EXPECTED_TEST_CASES = 1800


def fmt(x: float | None) -> str:
    """Format a number for markdown."""
    return "n/a" if x is None else f"{x:.3f}"


def render(tables: dict, tag: str) -> str:
    """Render the key Fishing results as markdown."""
    banner = f"**{tag}**\n\n" if tag else ""
    a = tables["label_a_any_change"]
    t = a["both_minus_actions_only"]
    b = tables["label_b_over_take_only"]["both_minus_actions_only"]
    return (
        f"{banner}# Fishing transfer (Amendment 1)\n\n"
        f"Cases {tables['n_cases']} in {tables['n_games']} games. Over-take "
        f"{tables['outcome_counts']['over_take']}, under-take "
        f"{tables['outcome_counts']['under_take']}, unchanged "
        f"{tables['outcome_counts']['unchanged']}.\n\n"
        f"Test (label a), Both minus Actions-only: pooled {fmt(t['diff'])}, mean of per-game "
        f"differences {fmt(t['mean_of_per_game_differences'])}, one-sided 5th percentile "
        f"{fmt(t['lower_95_one_sided'])}, success = {t['success']}.\n\n"
        f"Label (b), same contrast (descriptive): pooled {fmt(b['diff'])}, per-game mean "
        f"{fmt(b['mean_of_per_game_differences'])}, positives {b['n_positive']}, "
        f"negatives {b['n_negative']}.\n"
    )


def build(split: str, source_logs: dict, rows_by_view: dict, fits: dict) -> dict:
    """Assemble cases from the raw logs and run the Fishing analysis."""
    cases = []
    for source, log in source_logs.items():
        cases += fishing.fishing_cases(log, source, split=split)
    have = set.intersection(*(set(r) for r in rows_by_view.values()))
    cases = [c for c in cases if scoring.case_id(c) in have]
    tables = fishing_analysis.analyze(cases, rows_by_view, source_logs, fits)
    if split == "fishing_test":
        tables["shortfall_cases"] = EXPECTED_TEST_CASES - len(cases)
    return tables


def write(tables: dict, out: Path, tag: str) -> Path:
    """Write tables.json and tables.md."""
    out.mkdir(parents=True, exist_ok=True)
    tables = {"tag": tag, **tables}
    (out / "tables.json").write_text(analysis.canonical(tables) + "\n")
    (out / "tables.md").write_text(render(tables, tag))
    return out


def run_dev(out: Path = DEV_OUT) -> Path:
    """Analyse scores/fishing_dev (DEV-ONLY) with the frozen El Farol thresholds."""
    log = json.loads(splits.FISHING_PILOT_RAW.read_text(encoding="utf-8"))
    rows = load_dir(SCORES / "fishing_dev")
    fits = (
        (json.loads(splits.FROZEN.read_text()).get("thresholds") or {})
        if splits.FROZEN.exists()
        else {}
    )
    tables = build(
        "fishing_dev", {"fishpilot": log}, {v: rows[v] for v in ("both", "actions_only")}, fits
    )
    return write(tables, out, scoring.DEV_TAG)


def run_test(out: Path = TEST_OUT) -> Path:
    """Analyse scores/fishing_test; refused until the amendment URL and both batches exist."""
    splits.check_gate("fishing_test")
    frozen = base.require_frozen()
    logs = fishing.load_test_logs()
    rows = load_dir(SCORES / "fishing_test")
    fits = base.frozen_fits(frozen)
    present = {v: rows[v] for v in fishing_analysis.SCORED_VIEWS if v in rows}
    return write(build("fishing_test", logs, present, fits), out, "")


def main(argv: list[str] | None = None) -> None:
    """Command-line entry point."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev-only", action="store_true")
    args = ap.parse_args(argv)
    run_dev() if args.dev_only else run_test()


if __name__ == "__main__":
    main()
