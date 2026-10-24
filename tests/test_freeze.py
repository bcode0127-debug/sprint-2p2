"""Tests for scripts/freeze.py and scripts/fit_thresholds.py on throwaway repos."""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from scripts import fit_thresholds, freeze

from sprint2p2 import analysis, splits, views

NOW = datetime(2026, 10, 24, 9, 30, tzinfo=ZoneInfo("America/New_York"))
PREREG = "**DRAFT, NOT FROZEN**\n\n# Pre-registration\nPENDING, not blocking the freeze: title.\n"


def run(cwd: Path, *args: str) -> str:
    """Run a command and return stdout, ignoring git variables inherited from a hook."""
    done = subprocess.run(  # noqa: S603
        args,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        env=freeze.clean_git_env(),
    )
    return done.stdout.strip()


def make_repo(tmp_path: Path, prereg: str = PREREG) -> tuple[Path, Path]:
    """Create a small repo on main with a bare remote and every file freeze.py needs."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    remote = tmp_path / "remote.git"
    repo = tmp_path / "repo"
    repo.mkdir()
    run(tmp_path, "git", "init", "-q", "--bare", "-b", "main", str(remote))
    run(repo, "git", "init", "-q", "-b", "main")
    for key, value in (("user.name", "t"), ("user.email", "t@example.com")):
        run(repo, "git", "config", key, value)
    files = {
        "docs/preregistration.md": prereg,
        "prompts/monitor_prompt_v1.txt": "prompt",
        "configs/monitor.json": json.dumps({"model": "anthropic/claude-haiku-5.5"}),
        "src/sprint2p2/views.py": "views",
        "src/sprint2p2/metrics.py": "metrics",
        "scripts/analyze.py": "analyze",
        "results/model_pin.json": json.dumps(
            [{"requested": "gpt-5.2", "returned_model": "gpt-5.2-2025-12-11"}],
        ),
    }
    for rel, text in files.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text)
    run(repo, "git", "add", "-A")
    run(repo, "git", "commit", "-q", "-m", "init")
    run(repo, "git", "remote", "add", "origin", str(remote))
    run(repo, "git", "push", "-q", "origin", "main")
    return repo, remote


def test_problems_detects_fill_and_blocking_pending() -> None:
    """[FILL and a PENDING without 'not blocking' block the freeze."""
    assert freeze.problems("ok\nPENDING, not blocking the freeze: x") == []
    assert freeze.problems("see [FILL: date]") == ["contains [FILL"]
    assert freeze.problems("a\nPENDING: the label") == ["line 2: blocking PENDING"]


def test_stamp_replaces_draft_line() -> None:
    """The DRAFT line becomes FROZEN with the ET time; a missing line is an error."""
    out = freeze.stamp(PREREG, "2026-10-24T09:30:00-04:00")
    assert out.startswith("**FROZEN 2026-10-24T09:30:00-04:00**")
    assert "DRAFT" not in out
    with pytest.raises(freeze.FreezeError):
        freeze.stamp("no marker here", "x")


def test_freeze_end_to_end(tmp_path: Path) -> None:
    """Freeze stamps, commits, writes the record, commits again and pushes."""
    repo, remote = make_repo(tmp_path)
    record = freeze.freeze(repo, NOW)
    text = (repo / "docs" / "preregistration.md").read_text()
    assert text.startswith("**FROZEN 2026-10-24T09:30:00-04:00**")
    stored = json.loads((repo / "configs" / "frozen.json").read_text())
    assert stored == record
    assert stored["osf_url"] == ""
    assert stored["thresholds"] == {}
    assert stored["monitor_model"] == "anthropic/claude-haiku-5.5"
    assert stored["agent_model"]["resolved"] == "gpt-5.2-2025-12-11"
    assert stored["seeds"]["bootstrap_and_threshold_ties"] == 2026  # noqa: PLR2004
    assert stored["sha256"] == freeze.file_hashes(repo)
    assert stored["sha256"]["docs/preregistration.md"] == analysis.sha256(text)
    prereg_commit = run(repo, "git", "rev-parse", "HEAD~1")
    assert stored["prereg_commit"] == prereg_commit
    assert run(repo, "git", "log", "-1", "--format=%s", prereg_commit).startswith("Freeze pre-")
    assert run(remote, "git", "rev-parse", "main") == run(repo, "git", "rev-parse", "HEAD")


def test_freeze_refuses_unready_states(tmp_path: Path) -> None:
    """Blocking text, wrong branch and a dirty tree each stop the freeze."""
    repo, _ = make_repo(tmp_path / "a", PREREG + "PENDING: label\n")
    with pytest.raises(freeze.FreezeError, match="PENDING"):
        freeze.freeze(repo, NOW)
    repo, _ = make_repo(tmp_path / "b")
    run(repo, "git", "checkout", "-q", "-b", "feat/x")
    with pytest.raises(freeze.FreezeError, match="main"):
        freeze.freeze(repo, NOW)
    repo, _ = make_repo(tmp_path / "c")
    (repo / "scripts" / "analyze.py").write_text("edited")
    with pytest.raises(freeze.FreezeError, match="clean"):
        freeze.freeze(repo, NOW)


def write_threshold_scores(directory: Path) -> None:
    """Write tiny threshold-split score files for every scorer."""
    directory.mkdir(parents=True)
    for i, name in enumerate(analysis.SCORERS):
        rows = [
            {
                "id": f"main|{g}|1|A{k}",
                "game": f"main:{g}",
                "label": k % 2 == 0,
                "score": (k * 7 + i) % 10,
                "parse_ok": True,
            }
            for g in range(3)
            for k in range(10)
        ]
        (directory / f"{name}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))


def test_fit_thresholds_writes_all_views_and_opens_test_gate(tmp_path: Path) -> None:
    """fit_thresholds needs osf_url, then writes t and q that open the test gate."""
    frozen = tmp_path / "frozen.json"
    scores = tmp_path / "scores"
    write_threshold_scores(scores)
    frozen.write_text(json.dumps({"prereg_commit": "abc", "osf_url": ""}))
    with pytest.raises(splits.GateError):
        fit_thresholds.fit_thresholds(frozen, scores)
    frozen.write_text(json.dumps({"prereg_commit": "abc", "osf_url": "https://osf.io/x"}))
    with pytest.raises(splits.GateError):
        splits.check_gate("test", frozen)
    out = fit_thresholds.fit_thresholds(frozen, scores)
    assert set(out["thresholds"]) == set(analysis.SCORERS)
    assert all(v in out["thresholds"] for v in views.VIEWS)
    assert len(out["threshold_scores_sha256"]) == len(analysis.SCORERS)
    splits.check_gate("test", frozen)


def test_freeze_ignores_inherited_git_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """GIT_DIR and friends (exported by hooks and worktrees) must not redirect git elsewhere.

    A hook once pointed these at the real repository and the tests rewrote its config and files.
    """
    decoy = tmp_path / "decoy.git"
    for name in freeze.GIT_STRUCTURAL_VARS:
        monkeypatch.setenv(name, str(decoy))
    repo, remote = make_repo(tmp_path / "work")
    freeze.freeze(repo, NOW)
    assert not decoy.exists()
    assert run(remote, "git", "rev-parse", "main") == run(repo, "git", "rev-parse", "HEAD")
    assert (repo / "configs" / "frozen.json").exists()
