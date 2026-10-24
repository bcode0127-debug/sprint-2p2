"""Tests for the report figures and tables: every value equals its source to 3 decimals."""

import json
import re
from pathlib import Path

import numpy as np
import pytest
from scripts import make_figures as mf

ROOT = Path(__file__).resolve().parent.parent
AXIS = (0.40, 0.80)
TABLE1_COLS, TABLE2_COLS, TABLE2_ROWS, PNG_TOL = 8, 5, 8, 2
DATA = json.loads(mf.FIGURE_DATA.read_text(encoding="utf-8")) if mf.FIGURE_DATA.exists() else None
needs_data = pytest.mark.skipif(DATA is None, reason="run scripts.make_figures first")


def tables(run: str) -> dict:
    """Read a registered tables.json."""
    return mf.read_json(mf.TABLE_DIRS[run], "tables.json")


@needs_data
@pytest.mark.parametrize("run", ["test", "replication"])
def test_figure1_el_farol_matches_tables(run: str) -> None:
    """Every El Farol point and interval equals deployment_reading in tables.json."""
    dep = tables(run)["deployment_reading"]
    for view, point in DATA["figure1"][run].items():
        assert point["auroc"] == pytest.approx(dep[view]["auroc_test"], abs=5e-4)
        assert point["ci95"] == pytest.approx(dep[view]["auroc_ci95"], abs=5e-4)
    assert set(DATA["figure1"][run]) == {v for v, _ in mf.VIEW_ROWS}


@needs_data
def test_figure1_fishing_matches_tables() -> None:
    """The Fishing panel equals label (a) scorers and has no El Farol-only views."""
    scorers = tables("fishing")["label_a_any_change"]["scorers"]
    got = DATA["figure1"]["fishing"]
    assert set(got) == {"both", "actions_only", "empty"}
    for view, point in got.items():
        assert point["auroc"] == pytest.approx(scorers[view]["auroc"], abs=5e-4)
        assert point["ci95"] == pytest.approx(scorers[view]["auroc_ci95"], abs=5e-4)


@needs_data
def test_anchors() -> None:
    """The headline AUROCs and the Fishing direction anchors."""
    f1, f2 = DATA["figure1"], DATA["figure2"]
    expected = {
        "test": (0.655, 0.508),
        "replication": (0.668, 0.501),
        "fishing": (0.650, 0.536),
    }
    for run, (both, actions) in expected.items():
        assert f1[run]["both"]["auroc"] == pytest.approx(both, abs=5e-4)
        assert f1[run]["actions_only"]["auroc"] == pytest.approx(actions, abs=5e-4)
    assert f2["over"]["both"]["auroc"] == pytest.approx(0.570, abs=5e-4)
    assert f2["over"]["R2"]["auroc"] == pytest.approx(0.799, abs=5e-4)


@needs_data
def test_figure1_intervals_inside_axis() -> None:
    """No plotted interval is clipped by the 0.40 to 0.80 axis."""
    for run in DATA["figure1"].values():
        for point in run.values():
            assert AXIS[0] <= point["ci95"][0] <= point["auroc"] <= point["ci95"][1] <= AXIS[1]


@needs_data
def test_figure2_points_inside_interval_and_counts() -> None:
    """Direction points sit inside their intervals; class counts add up to the outcome counts."""
    counts = tables("fishing")["outcome_counts"]
    assert DATA["figure2"]["under"]["n_positive"] == counts["under_take"]
    assert DATA["figure2"]["over"]["n_positive"] == counts["over_take"]
    for key in ("under", "over"):
        assert DATA["figure2"][key]["n_unchanged"] == counts["unchanged"]
        for m, _ in mf.METHODS:
            e = DATA["figure2"][key][m]
            assert e["ci95"][0] <= e["auroc"] <= e["ci95"][1]


@needs_data
def test_figure3_matches_sources() -> None:
    """Achieved FPR points equal the stored fpr_achieved and recalibration values."""
    f3 = DATA["figure3"]
    assert f3["test"]["value"] == pytest.approx(
        tables("test")["deployment_reading"]["both"]["fpr_achieved"], abs=5e-4
    )
    assert f3["replication_all"]["value"] == pytest.approx(
        tables("replication")["deployment_reading"]["both"]["fpr_achieved"], abs=5e-4
    )
    held = mf.read_json("replication", "recalibration.json")["views"]["both"]["trials_10_to_19"]
    assert f3["replication_10_19_frozen"]["value"] == pytest.approx(held["frozen"]["fpr"], abs=5e-4)
    assert f3["replication_10_19_refit"]["value"] == pytest.approx(held["refit"]["fpr"], abs=5e-4)
    fish = tables("fishing")["label_a_any_change"]["deployment"]["both"]["fpr_achieved"]
    assert f3["fishing"]["value"] == pytest.approx(fish, abs=5e-4)
    for e in f3.values():
        assert e["ci95"][0] <= e["value"] <= e["ci95"][1]


@needs_data
def test_report_tables_match_sources() -> None:
    """Every Table 1 and Table 2 value in the markdown equals the source value."""
    text = mf.REPORT_TABLES.read_text(encoding="utf-8")
    rows = [line.split("|")[1:-1] for line in text.splitlines() if line.startswith("| El Farol")]
    rows += [line.split("|")[1:-1] for line in text.splitlines() if line.startswith("| Fishing")]
    cells = [[c.strip() for c in r] for r in rows]
    t1 = {c[0]: c for c in cells if len(c) == TABLE1_COLS}
    for run in ("test", "replication", "fishing"):
        t = tables(run)
        row = t1[mf.RUN_LABELS[run]]
        if run == "fishing":
            a = t["label_a_any_change"]
            want = [
                a["scorers"]["both"]["auroc"],
                a["scorers"]["actions_only"]["auroc"],
                a["both_minus_actions_only"]["diff"],
                a["both_minus_actions_only"]["lower_95_one_sided"],
                a["both_minus_actions_only"]["mean_of_per_game_differences"],
            ]
        else:
            p = t["primary"]
            per_game = (
                mf.read_json("replication", "extras.json")["primary"][
                    "mean_of_per_game_differences"
                ]
                if run == "replication"
                else p["power"]["auroc"]["mean_of_per_game_differences"]
            )
            want = [p["auroc_a"], p["auroc_b"], p["diff"], p["lower_95_one_sided"], per_game]
        got = [float(x) for x in row[3:]]
        assert got == pytest.approx(want, abs=5e-4)
    t2 = [c for c in cells if len(c) == TABLE2_COLS]
    assert len(t2) == TABLE2_ROWS
    comb = mf.read_json("replication", "extras.json")["combination"]
    for run, name, diff, lower, p_holm in t2:
        key = "test" if run == "El Farol test" else "replication"
        src = comb[name] if name in comb else tables(key)["secondary"][name]
        assert float(diff) == pytest.approx(src["diff"], abs=5e-4)
        assert float(lower) == pytest.approx(src["lower_95_one_sided"], abs=5e-4)
        assert float(p_holm) == pytest.approx(src["p_holm"], abs=5e-5)


def test_fpr_bootstrap_resamples_games() -> None:
    """On two games with FPR 0 and 1 the interval spans the whole range, and a constant is exact."""
    games = ["a"] * 10 + ["b"] * 10
    labels = np.zeros(20, bool)
    flags = np.array([False] * 10 + [True] * 10)
    low, high = mf.fpr_bootstrap(flags, labels, games)
    assert (low, high) == (0.0, 1.0)
    assert mf.fpr_bootstrap(np.ones(20, bool), labels, games) == [1.0, 1.0]


def test_no_em_dashes_in_outputs() -> None:
    """The script, tables and test contain no em dashes."""
    dash = chr(0x2014)
    for path in (Path(mf.__file__), mf.REPORT_TABLES, Path(__file__)):
        if path.exists():
            assert dash not in path.read_text(encoding="utf-8")


@needs_data
def test_figure_files_exist_and_are_one_column_wide() -> None:
    """PNG at 300 dpi and PDF exist for each figure; PNG width is 6.5 in at 300 dpi."""
    for stem in ("figure1_auroc_by_view", "figure2_fishing_direction", "figure3_threshold_drift"):
        png = mf.FIGURES / f"{stem}.png"
        assert (mf.FIGURES / f"{stem}.pdf").stat().st_size > 0
        header = png.read_bytes()[:24]
        width = int.from_bytes(header[16:20], "big")
        assert abs(width - round(mf.WIDTH * 300)) <= PNG_TOL
    assert re.fullmatch(r"#[0-9A-Fa-f]{6}", mf.ACCENT)
