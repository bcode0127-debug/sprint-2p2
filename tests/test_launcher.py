"""Tests for scripts/run_games.sh (dry runs against a temporary output directory only)."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "run_games.sh"
PIN = ROOT / "results" / "model_pin.json"


def run(out_root: Path, *args: str) -> subprocess.CompletedProcess:
    """Run the launcher with its output root pointed at a temporary directory."""
    env = {**os.environ, "HARNESS_OUT_ROOT": str(out_root)}
    return subprocess.run(  # noqa: S603
        ["bash", str(SCRIPT), *args],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def output_file(out_root: Path, game: str, suffix: str) -> Path:
    """Return the harness output path for a game and run suffix under the temporary root."""
    return out_root / game / "5agents" / f"gpt-5.2_endogenous_{suffix}.json"


def test_syntax() -> None:
    """The script passes a bash syntax check."""
    assert subprocess.run(["bash", "-n", str(SCRIPT)], check=False).returncode == 0  # noqa: S603, S607


@pytest.mark.parametrize("batch", ["A", "B"])
def test_dry_run_succeeds_when_the_output_file_is_absent(batch: str, tmp_path: Path) -> None:
    """With no output file: pin, harness command and pin are printed, and nothing is written."""
    before = PIN.read_bytes()
    out = run(tmp_path, "fishing-test", batch, "--dry-run")
    assert out.returncode == 0
    lines = [ln for ln in out.stdout.splitlines() if ln.startswith("+ ")]
    assert len(lines) == 3  # noqa: PLR2004
    assert f"model_pin.py before_fishtest{batch}" in lines[0]
    assert "--game fishing --agents 5 --trials 20 --rounds 10 --model gpt-5.2" in lines[1]
    assert f"--run-suffix fishtest{batch}" in lines[1]
    assert f"model_pin.py after_fishtest{batch}" in lines[2]
    assert PIN.read_bytes() == before
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("batch", ["A", "B"])
def test_dry_run_is_refused_when_the_output_file_exists(batch: str, tmp_path: Path) -> None:
    """With the output file present the launcher refuses (exit 3) and prints no command."""
    target = output_file(tmp_path, "fishing", f"fishtest{batch}")
    target.parent.mkdir(parents=True)
    target.write_text("{}")
    out = run(tmp_path, "fishing-test", batch, "--dry-run")
    assert out.returncode == 3  # noqa: PLR2004
    assert "refusing" in out.stderr
    assert str(target) in out.stderr
    assert "+ " not in out.stdout


def test_batch_a_guard_does_not_depend_on_batch_b(tmp_path: Path) -> None:
    """Only the batch's own file blocks it: an existing batch A does not block batch B."""
    target = output_file(tmp_path, "fishing", "fishtestA")
    target.parent.mkdir(parents=True)
    target.write_text("{}")
    assert run(tmp_path, "fishing-test", "A", "--dry-run").returncode == 3  # noqa: PLR2004
    assert run(tmp_path, "fishing-test", "B", "--dry-run").returncode == 0


def test_bad_arguments_and_old_mode_overwrite_guard(tmp_path: Path) -> None:
    """Unknown batches and flags are rejected; the two-game mode honours the same guard."""
    assert run(tmp_path, "fishing-test", "C", "--dry-run").returncode == 2  # noqa: PLR2004
    assert run(tmp_path, "fishing-test", "A", "--wet").returncode == 2  # noqa: PLR2004
    target = output_file(tmp_path, "elfarol", "main")
    target.parent.mkdir(parents=True)
    target.write_text("{}")
    out = run(tmp_path, "1", "0", "main", "main")
    assert out.returncode == 3  # noqa: PLR2004
    assert "refusing" in out.stderr
