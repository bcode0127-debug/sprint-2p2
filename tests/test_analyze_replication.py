"""Tests for scripts/analyze_replication.py."""

import json
from pathlib import Path

import pytest
from scripts import analyze_replication

from sprint2p2 import splits

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "results" / "tables" / "final"


def test_pointed_at_test_split_is_byte_identical(tmp_path: Path) -> None:
    """Same code path with the test split: tables.json and tables.md match the registered run."""
    analyze_replication.run("test", tmp_path)
    assert (tmp_path / "tables.json").read_bytes() == (FINAL / "tables.json").read_bytes()
    assert (tmp_path / "tables.md").read_bytes() == (FINAL / "tables.md").read_bytes()
    extra = json.loads((tmp_path / "extras.json").read_text())
    assert (
        "mean_of_per_game_differences"
        not in (tmp_path / "tables.json").read_text().split("power")[0]
    )
    assert round(extra["primary"]["pooled_difference"], 3) == 0.147  # noqa: PLR2004
    assert round(extra["primary"]["mean_of_per_game_differences"], 3) == 0.117  # noqa: PLR2004
    assert round(extra["combination"]["C1"]["diff"], 3) == 0.043  # noqa: PLR2004
    assert round(extra["combination"]["C2"]["mean_of_per_game_differences"], 3) == -0.003  # noqa: PLR2004


def test_replication_split_is_refused_without_amendment_url(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """With amendment1_url removed from the freeze file, the replication analysis refuses to run."""
    frozen = json.loads((ROOT / "configs" / "frozen.json").read_text())
    for key in ("amendment1_url", "amendment1_sha256"):
        frozen.pop(key, None)
    path = tmp_path / "frozen.json"
    path.write_text(json.dumps(frozen))
    monkeypatch.setattr(splits, "FROZEN", path)
    with pytest.raises(splits.GateError):
        analyze_replication.run("replication", tmp_path / "out")
    assert not (tmp_path / "out" / "tables.json").exists()
