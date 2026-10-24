"""Report figures and tables from the registered results (no API calls).

    PYTHONPATH=src .venv/bin/python -m scripts.make_figures

Reads results/tables/{final,replication,fishing_test}/ and the score files in scores/. Writes
results/figures/figure_data.json (every plotted value), figure1 to figure3 as PNG (300 dpi) and
PDF, and results/report_tables.md. Intervals not already in a tables.json (the Fishing direction
AUROCs and the achieved FPR) are game bootstraps with the project's seed and resample count.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from scripts import analyze as base
from scripts._scores import SCORES, load_dir
from scripts.recalibrate_replication import APPLY_TRIALS, subset
from sprint2p2 import analysis, fishing, fishing_analysis, metrics, scoring

ROOT = Path(__file__).resolve().parent.parent
TABLES = ROOT / "results" / "tables"
FIGURES = ROOT / "results" / "figures"
REPORT_TABLES = ROOT / "results" / "report_tables.md"
FIGURE_DATA = FIGURES / "figure_data.json"

WIDTH = 6.5
ACCENT = "#0072B2"
GREY = "#6e6e6e"
LIGHT = "#a8a8a8"
FONT = 9
VIEW_ROWS = (
    ("both", "Both"),
    ("messages_only", "Messages-only"),
    ("structured", "Structured"),
    ("own_only", "Own-only"),
    ("freshness", "Freshness"),
    ("actions_only", "Actions-only"),
    ("counting", "Counting rule"),
    ("empty", "Empty"),
)
FIG1_RUNS = ("test", "replication", "fishing")
RUN_LABELS = {"test": "El Farol test", "replication": "El Farol replication", "fishing": "Fishing"}
DIRECTIONS = (("under", "Took less than announced"), ("over", "Took more than announced"))
METHODS = (("both", "Both (monitor)"), ("R2", "Rule R2"), ("R1", "Rule R1"))
TABLE_DIRS = {"test": "final", "replication": "replication", "fishing": "fishing_test"}


def read_json(*parts: str) -> dict:
    """Read a JSON file under results/tables."""
    return json.loads(TABLES.joinpath(*parts).read_text(encoding="utf-8"))


def fpr_bootstrap(flags: np.ndarray, labels: np.ndarray, games: list[str]) -> list[float]:
    """Two-sided 95% game-bootstrap interval of the achieved FPR (flags are fixed)."""
    f, lab = np.asarray(flags, bool), np.asarray(labels, bool)
    groups = metrics._groups(games)  # noqa: SLF001
    rng = np.random.default_rng(metrics.SEED)
    values = []
    for _ in range(metrics.N_BOOT):
        idx = np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        neg = ~lab[idx]
        if neg.any():
            values.append(float(f[idx][neg].mean()))
    low, high = np.percentile(values, [2.5, 97.5])
    return [float(low), float(high)]


def fpr_entry(rows: dict, fit: dict) -> dict:
    """Achieved FPR of a fit on a set of score rows, with its game-bootstrap interval."""
    ids = sorted(rows)
    scores, _ = analysis.arrays(rows, ids)
    labels, games = analysis.labels_games(rows, ids)
    flagged = metrics.flags(scores, ids, fit)
    return {
        "value": float(flagged[~labels].mean()),
        "ci95": fpr_bootstrap(flagged, labels, games),
        "n_keep": int((~labels).sum()),
    }


def fishing_inputs() -> dict:
    """Rebuild the Fishing test cases, scores and rules exactly as scripts.analyze_fishing does."""
    logs = fishing.load_test_logs()
    rows = load_dir(SCORES / "fishing_test")
    present = {v: rows[v] for v in fishing_analysis.SCORED_VIEWS if v in rows}
    cases = []
    for source, log in logs.items():
        cases += fishing.fishing_cases(log, source, split="fishing_test")
    have = set.intersection(*(set(r) for r in present.values()))
    cases = [c for c in cases if scoring.case_id(c) in have]
    ids = [scoring.case_id(c) for c in cases]
    return {
        "cases": cases,
        "ids": ids,
        "games": [c["game"] for c in cases],
        "label_a": np.array([c["label"] for c in cases], bool),
        "label_b": np.array([c["label_over"] for c in cases], bool),
        "scores": {v: analysis.arrays(r, ids)[0] for v, r in present.items()},
        "rules": fishing_analysis.rule_arrays(cases, logs),
    }


def direction_entries(fi: dict) -> dict:
    """AUROC against unchanged catches for each direction, Both vs rule R2 vs rule R1."""
    under = fi["label_a"] & ~fi["label_b"]
    unchanged = ~fi["label_a"]
    series = {"both": fi["scores"]["both"], "R2": fi["rules"]["R2"], "R1": fi["rules"]["R1"]}
    out = {}
    for key, positive in (("under", under), ("over", fi["label_b"])):
        keep = positive | unchanged
        games = [g for g, k in zip(fi["games"], keep, strict=True) if k]
        out[key] = {
            "n_positive": int(positive.sum()),
            "n_unchanged": int(unchanged.sum()),
            **{
                m: {
                    "auroc": metrics.auroc(s[keep], positive[keep]),
                    "ci95": metrics.auroc_ci(s[keep], positive[keep], games),
                }
                for m, s in series.items()
            },
        }
    return out


def fig1_data() -> dict:
    """Per run and view: AUROC and 95% interval, read from the tables."""
    out = {}
    for run in ("test", "replication"):
        dep = read_json(TABLE_DIRS[run], "tables.json")["deployment_reading"]
        out[run] = {
            v: {"auroc": dep[v]["auroc_test"], "ci95": dep[v]["auroc_ci95"]}
            for v, _ in VIEW_ROWS
            if v in dep
        }
    scorers = read_json("fishing_test", "tables.json")["label_a_any_change"]["scorers"]
    out["fishing"] = {
        v: {"auroc": scorers[v]["auroc"], "ci95": scorers[v]["auroc_ci95"]}
        for v, _ in VIEW_ROWS
        if v in scorers
    }
    return out


def fig3_data(fi: dict) -> dict:
    """Achieved FPR of Both at the frozen threshold (and the refit one) with game intervals."""
    fits = base.frozen_fits(base.require_frozen())
    refit = read_json("replication", "recalibration.json")["views"]["both"]
    rep = load_dir(SCORES / "replication")["both"]
    held = subset(rep, APPLY_TRIALS)
    ids = fi["ids"]
    flagged = metrics.flags(fi["scores"]["both"], ids, fits["both"])
    neg = ~fi["label_a"]
    fish = {
        "value": float(flagged[neg].mean()),
        "ci95": fpr_bootstrap(flagged, fi["label_a"], fi["games"]),
        "n_keep": int(neg.sum()),
    }
    return {
        "test": fpr_entry(load_dir(SCORES / "test")["both"], fits["both"]),
        "replication_all": fpr_entry(rep, fits["both"]),
        "replication_10_19_frozen": fpr_entry(held, fits["both"]),
        "replication_10_19_refit": fpr_entry(held, refit["refit_on_trials_0_to_9"]),
        "fishing": fish,
    }


def table1() -> list[dict]:
    """One row per run for report Table 1, read from tables.json."""
    rows = []
    for run in FIG1_RUNS:
        t = read_json(TABLE_DIRS[run], "tables.json")
        if run == "fishing":
            a = t["label_a_any_change"]
            c = a["both_minus_actions_only"]
            sc = a["scorers"]
            rows.append(
                {
                    "run": run,
                    "games": t["n_games"],
                    "breaks": a["counts"]["n_positive"],
                    "both": sc["both"]["auroc"],
                    "actions_only": sc["actions_only"]["auroc"],
                    "diff": c["diff"],
                    "lower": c["lower_95_one_sided"],
                    "per_game": c["mean_of_per_game_differences"],
                }
            )
            continue
        p = t["primary"]
        dep = t["deployment_reading"]["both"]
        per_game = (
            read_json("replication", "extras.json")["primary"]["mean_of_per_game_differences"]
            if run == "replication"
            else p["power"]["auroc"]["mean_of_per_game_differences"]
        )
        rows.append(
            {
                "run": run,
                "games": p["n_games"],
                "breaks": dep["n_break"],
                "both": p["auroc_a"],
                "actions_only": p["auroc_b"],
                "diff": p["diff"],
                "lower": p["lower_95_one_sided"],
                "per_game": per_game,
            }
        )
    return rows


def table2() -> list[dict]:
    """S1 to S3 for test and replication, C1 and C2 for replication."""
    rows = []
    for run in ("test", "replication"):
        sec = read_json(TABLE_DIRS[run], "tables.json")["secondary"]
        rows += [
            {
                "run": run,
                "contrast": k,
                "diff": sec[k]["diff"],
                "lower": sec[k]["lower_95_one_sided"],
                "p_holm": sec[k]["p_holm"],
            }
            for k in ("S1", "S2", "S3")
        ]
    comb = read_json("replication", "extras.json")["combination"]
    rows += [
        {
            "run": "replication",
            "contrast": k,
            "diff": comb[k]["diff"],
            "lower": comb[k]["lower_95_one_sided"],
            "p_holm": comb[k]["p_holm"],
        }
        for k in ("C1", "C2")
    ]
    return rows


def collect() -> dict:
    """Gather every plotted and tabulated value."""
    fi = fishing_inputs()
    return {
        "seed": metrics.SEED,
        "n_resamples": metrics.N_BOOT,
        "figure1": fig1_data(),
        "figure2": direction_entries(fi),
        "figure3": fig3_data(fi),
        "table1": table1(),
        "table2": table2(),
    }


def render_tables(data: dict) -> str:
    """Render report Tables 1 and 2 as markdown."""
    f3, f4 = "{:.3f}", "{:.4f}"
    t1 = [
        (
            "| Run | Games | Breaks | Both AUROC | Actions-only AUROC | Pooled difference "
            "| One-sided 5th percentile | Per-game mean |"
        ),
        "|---|---|---|---|---|---|---|---|",
    ]
    t1.extend(
        f"| {RUN_LABELS[r['run']]} | {r['games']} | {r['breaks']} | {f3.format(r['both'])} "
        f"| {f3.format(r['actions_only'])} | {f3.format(r['diff'])} "
        f"| {f3.format(r['lower'])} | {f3.format(r['per_game'])} |"
        for r in data["table1"]
    )
    t2 = [
        "| Run | Contrast | Difference | One-sided 5th percentile | Holm p |",
        "|---|---|---|---|---|",
    ]
    t2.extend(
        f"| {RUN_LABELS[r['run']]} | {r['contrast']} | {f3.format(r['diff'])} "
        f"| {f3.format(r['lower'])} | {f4.format(r['p_holm'])} |"
        for r in data["table2"]
    )
    return (
        "# Report tables\n\nGenerated by scripts/make_figures.py from results/tables/*/tables.json "
        "and extras.json. Registered results only.\n\n"
        "## Table 1\n\nBoth minus Actions-only by run. Breaks are positive cases (Fishing: any "
        "change from the announcement).\n\n" + "\n".join(t1) + "\n\n## Table 2\n\n"
        "Both minus the comparison view (S1 Own-only, S2 Freshness, S3 counting rule) and Both "
        "minus the combination (C1, C2). Holm p-values are the stored ones.\n\n"
        + "\n".join(t2)
        + "\n"
    )


def style() -> None:
    """Apply the common matplotlib style."""
    plt.switch_backend("Agg")
    plt.rcParams.update(
        {
            "font.size": FONT,
            "axes.labelsize": FONT,
            "xtick.labelsize": FONT,
            "ytick.labelsize": FONT,
            "legend.fontsize": FONT,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "pdf.fonttype": 42,
        }
    )


def interval(ax: plt.Axes, y: float, point: dict, color: str, marker: str = "o") -> None:
    """Draw a point with its interval on a horizontal axis."""
    lo, hi = point["ci95"]
    ax.hlines(y, lo, hi, color=color, lw=1.6)
    ax.plot(point["auroc"], y, marker, color=color, ms=5.5)


def fig1(data: dict, stem: Path) -> None:
    """Figure 1: AUROC by view, three panels."""
    fig, axes = plt.subplots(1, 3, figsize=(WIDTH, 3.2), sharex=True, sharey=True)
    ys = {v: len(VIEW_ROWS) - i for i, (v, _) in enumerate(VIEW_ROWS)}
    for ax, run in zip(axes, FIG1_RUNS, strict=True):
        ax.axvline(0.5, color=LIGHT, ls="--", lw=1)
        for v, point in data["figure1"][run].items():
            interval(ax, ys[v], point, ACCENT if v == "both" else GREY)
        ax.set_xlim(0.40, 0.80)
        ax.set_xticks([0.4, 0.5, 0.6, 0.7, 0.8])
        ax.set_xticklabels(["0.4", "0.5", "0.6", "0.7", "0.8"], rotation=0)
        ax.set_ylim(0.4, len(VIEW_ROWS) + 0.6)
        ax.text(0.5, 1.02, RUN_LABELS[run], transform=ax.transAxes, ha="center", va="bottom")
        ax.set_xlabel("AUROC")
    axes[0].set_yticks(list(ys.values()), [n for _, n in VIEW_ROWS])
    fig.tight_layout(w_pad=0.6)
    save(fig, stem)


def fig2(data: dict, stem: Path) -> None:
    """Figure 2: Fishing AUROC by direction against unchanged catches."""
    fig, ax = plt.subplots(figsize=(WIDTH, 3.0))
    ax.axvline(0.5, color=LIGHT, ls="--", lw=1)
    colors = {"both": ACCENT, "R2": GREY, "R1": LIGHT}
    markers = {"both": "o", "R2": "s", "R1": "^"}
    ticks, labels = [], []
    y = 0.0
    for key, name in reversed(DIRECTIONS):
        for m, mname in METHODS:
            interval(ax, y, data["figure2"][key][m], colors[m], markers[m])
            ticks.append(y)
            labels.append(mname)
            y += 1
        ax.text(0.105, y, name, va="center", fontweight="bold")
        y += 1.2
    ax.set_yticks(ticks, labels)
    ax.set_ylim(-0.7, y - 0.9)
    ax.set_xlim(0.1, 1.0)
    ax.set_xlabel("AUROC against unchanged catches")
    fig.tight_layout()
    save(fig, stem)


def fig3(data: dict, stem: Path) -> None:
    """Figure 3: achieved FPR of Both at the frozen threshold."""
    rows = (
        ("test", "Test, frozen", ACCENT, "o"),
        ("replication_all", "Replication, frozen\n(all 20 games)", ACCENT, "o"),
        ("replication_10_19_frozen", "Replication trials 10-19,\nfrozen", ACCENT, "o"),
        ("replication_10_19_refit", "Replication trials 10-19,\nrefit", GREY, "s"),
        ("fishing", "Fishing, frozen", ACCENT, "o"),
    )
    fig, ax = plt.subplots(figsize=(WIDTH, 3.0))
    ax.axvline(0.10, color=LIGHT, ls="--", lw=1)
    for i, (key, _, color, marker) in enumerate(rows):
        e = data["figure3"][key]
        interval(ax, len(rows) - i, {"auroc": e["value"], "ci95": e["ci95"]}, color, marker)
    ax.set_yticks([len(rows) - i for i in range(len(rows))], [r[1] for r in rows])
    ax.set_ylim(0.4, len(rows) + 0.6)
    ax.set_xlim(0, 0.35)
    ax.set_xlabel("Achieved false-positive rate (target 0.10, dashed)")
    fig.tight_layout()
    save(fig, stem)


def save(fig: plt.Figure, stem: Path) -> None:
    """Write PNG (300 dpi) and PDF."""
    fig.savefig(stem.with_suffix(".png"), dpi=300)
    fig.savefig(stem.with_suffix(".pdf"))
    plt.close(fig)


def main() -> None:
    """Build all figures and tables."""
    FIGURES.mkdir(parents=True, exist_ok=True)
    data = collect()
    FIGURE_DATA.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_TABLES.write_text(render_tables(data), encoding="utf-8")
    style()
    fig1(data, FIGURES / "figure1_auroc_by_view")
    fig2(data, FIGURES / "figure2_fishing_direction")
    fig3(data, FIGURES / "figure3_threshold_drift")


if __name__ == "__main__":
    main()
