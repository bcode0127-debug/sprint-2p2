"""Turn score files into results/tables (primary, S1 to S3, controls, baselines).

Run from the project root with: PYTHONPATH=src .venv/bin/python -m scripts.analyze [--dev-only]
Dev-only mode uses dev for both the threshold and test roles and labels every output DEV-ONLY.
"""

import argparse
from pathlib import Path

from scripts._scores import pick
from sprint2p2 import analysis

ROOT = Path(__file__).resolve().parent.parent


def md_table(rows: dict[str, dict]) -> str:
    """Render a name-keyed table of evaluate() results as markdown."""
    head = "| scorer | AUROC | recall | FPR achieved | parse failures |\n|---|---|---|---|---|\n"
    body = "".join(
        f"| {n} | {r['auroc_test']:.3f} | {r['recall']:.3f} | "
        f"{r['fpr_achieved']:.3f} | {r['parse_failures']} |\n"
        for n, r in rows.items()
    )
    return head + body


def main() -> None:
    """Write results/tables/<tag>/ tables for the scores on disk."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev-only", action="store_true")
    args = ap.parse_args()
    thr, tst, tag = pick(dev_only=args.dev_only)
    tables = analysis.analyze(thr, tst, tag)
    out = ROOT / "results" / "tables" / (tag or "final")
    out.mkdir(parents=True, exist_ok=True)
    banner = f"**{tag}**\n\n" if tag else ""
    (out / "tables.json").write_text(analysis.canonical(tables) + "\n")
    primary = tables["primary"]
    sections = [
        f"{banner}# Result tables\n",
        "## Primary\n",
        md_table({primary["view"]: primary}),
        (
            f"\nvs {primary['comparator']}: diff {primary['vs_comparator']['diff']:.3f}, "
            f"one-sided 95% lower bound {primary['vs_comparator']['lower_95_one_sided']:.3f}\n"
        ),
        "## S1 to S3 (Holm-adjusted)\n",
        "| id | view | diff | lower 95% | p | p Holm |\n|---|---|---|---|---|---|\n",
        *(
            f"| {k} | {v['view']} | {v['diff']:.3f} | {v['lower_95_one_sided']:.3f} | "
            f"{v['p_one_sided']:.3f} | {v['p_holm']:.3f} |\n"
            for k, v in tables["secondary"].items()
        ),
        "\n## Ablations\n",
        md_table(tables["ablations"]),
        "\n## Controls\n",
        md_table(tables["controls"]),
        "\n## Baselines\n",
        md_table(tables["baselines"]),
    ]
    (out / "tables.md").write_text("\n".join(sections))


if __name__ == "__main__":
    main()
