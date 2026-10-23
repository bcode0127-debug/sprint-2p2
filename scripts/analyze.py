"""Analysis per pre-registration v2, sections 6 to 8, into results/tables.

Run from the project root with: PYTHONPATH=src .venv/bin/python -m scripts.analyze [--dev-only]
Without --dev-only the threshold and test splits are used, and the script refuses to run unless
configs/frozen.json exists. --dev-only uses development data for both roles and labels every output
DEV-ONLY.
"""

import argparse
import json
from pathlib import Path

from scripts._scores import SCORES, load_dir, pick
from sprint2p2 import analysis, baselines, splits
from sprint2p2.views import _trial

ROOT = Path(__file__).resolve().parent.parent
ROUND0_DIRNAME = "round0"


def require_frozen(path: Path | None = None) -> dict:
    """Refuse to analyse the threshold and test splits unless the freeze file exists."""
    path = path or splits.FROZEN
    if not path.exists():
        msg = f"{path.name} not found: the threshold and test splits are refused before the freeze"
        raise splits.GateError(msg)
    return json.loads(path.read_text())


def frozen_fits(frozen: dict) -> dict[str, dict]:
    """Read the per-scorer (t, q) written by scripts/fit_thresholds.py."""
    fits = frozen.get("thresholds") or {}
    missing = [n for n in analysis.SCORERS if n not in fits]
    if missing:
        msg = f"frozen.json has no thresholds for: {', '.join(missing)}"
        raise splits.GateError(msg)
    return fits


def build_meta(logs: dict, split: str, split_dir: Path) -> dict:
    """Typology per case and the round-0 rows (rules from raw logs, views if scored)."""
    cases = splits.split_cases(logs, split)
    typology = {
        f"{c['source']}|{c['trial']}|{c['round']}|{c['agent']}": _trial(
            logs[c["source"]],
            c["round"],
            c["trial"],
        )["agents"][c["agent"]].get("typology", "other")
        for c in cases
    }
    zero = splits.split_cases(logs, split, round_zero=True)
    ids = [f"{c['source']}|{c['trial']}|{c['round']}|{c['agent']}" for c in zero]
    scores = baselines.score_all(logs, zero, {})
    rows = {
        name: {
            i: {"id": i, "game": c["game"], "label": c["label"], "score": v, "parse_ok": True}
            for i, c, v in zip(ids, zero, scores[name], strict=True)
        }
        for name in analysis.ROUND0_RULES
    }
    rows.update(
        load_dir(split_dir / ROUND0_DIRNAME) if (split_dir / ROUND0_DIRNAME).is_dir() else {}
    )
    return {"typology": typology, "round0": rows}


def fmt(x: float | None) -> str:
    """Format a number for markdown."""
    return "n/a" if x is None else f"{x:.3f}"


def render(tables: dict) -> str:
    """Render the main tables as markdown."""
    banner = f"**{tables['tag']}**\n\n" if tables["tag"] else ""
    p = tables["primary"]
    lines = [
        f"{banner}# Result tables (pre-registration v2)\n",
        "## Primary: paired AUROC difference, Both minus Actions-only\n",
        (
            f"AUROC {fmt(p['auroc_a'])} vs {fmt(p['auroc_b'])}; difference {fmt(p['diff'])}; "
            f"one-sided 95% lower bound {fmt(p['lower_95_one_sided'])}; success = {p['success']}; "
            f"two-sided 95% interval (descriptive) {fmt(p['descriptive_two_sided_ci95'][0])} to "
            f"{fmt(p['descriptive_two_sided_ci95'][1])}\n"
        ),
        "## S1 to S3 (AUROC, one-sided, Holm at 0.05)\n",
        "| id | A minus B | diff | lower 95% | p | p Holm | reject | two-sided 95% (descriptive) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for k, v in tables["secondary"].items():
        lines.append(
            f"| {k} | {v['a']} - {v['b']} | {fmt(v['diff'])} | {fmt(v['lower_95_one_sided'])} | "
            f"{fmt(v['p_one_sided'])} | {fmt(v['p_holm'])} | {v['reject_at_0.05']} | "
            f"{fmt(v['descriptive_two_sided_ci95'][0])} to "
            f"{fmt(v['descriptive_two_sided_ci95'][1])} |",
        )
    lines += [
        "\n## Deployment reading: recall at the frozen 10% FPR\n",
        "| scorer | AUROC | recall | recall lower 95% | FPR achieved | parse failures |",
        "|---|---|---|---|---|---|",
    ]
    for n, r in tables["deployment_reading"].items():
        lines.append(
            f"| {n} | {fmt(r['auroc_test'])} | {fmt(r['recall'])} | "
            f"{fmt(r['recall_lower_95_one_sided'])} | {fmt(r['fpr_achieved'])} | "
            f"{r['parse_failures']} |",
        )
    c = tables["controls"]
    lines += [
        "\n## Controls\n",
        (
            f"- oracle: recall {fmt(c['oracle']['recall'])}, AUROC {fmt(c['oracle']['auroc'])}, "
            f"pass = {c['oracle']['pass']}"
        ),
        f"- empty: AUROC {fmt(c['empty']['auroc'])}, pass = {c['empty']['pass']}",
        (
            "- round_only vs round_rate: AUROC difference "
            f"{fmt(c['round_only_vs_round_rate']['auroc_difference'])}"
        ),
        (
            f"- plan rule: recall {fmt(c['plan_rule']['recall'])}, "
            f"FPR {fmt(c['plan_rule']['fpr'])} (expected near 0.32 and 0.11)"
        ),
        "\n## Power (minimum detectable difference, 20 games)\n",
        "| contrast | metric | between-game SD | min detectable |",
        "|---|---|---|---|",
    ]
    for key, per_metric in tables["power"].items():
        for m, e in per_metric.items():
            lines.append(
                f"| {key} | {m} | {fmt(e['between_game_sd'])} | "
                f"{fmt(e['min_detectable_difference_20_games'])} |",
            )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    """Write results/tables/<tag>/tables.json and tables.md."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev-only", action="store_true")
    args = ap.parse_args(argv)
    fits = None
    if not args.dev_only:
        fits = frozen_fits(require_frozen())
    thr, tst, tag = pick(dev_only=args.dev_only)
    split = "dev" if args.dev_only else "test"
    logs = splits.load_logs()
    meta = build_meta(logs, split, SCORES / split)
    tables = analysis.analyze(thr, tst, tag, fits, meta)
    out = ROOT / "results" / "tables" / (tag or "final")
    out.mkdir(parents=True, exist_ok=True)
    (out / "tables.json").write_text(analysis.canonical(tables) + "\n")
    (out / "tables.md").write_text(render(tables))


if __name__ == "__main__":
    main()
