"""Tests for scripts/run_games.sh (dry runs only; nothing is generated)."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "run_games.sh"
PIN = ROOT / "results" / "model_pin.json"


def run(*args: str) -> subprocess.CompletedProcess:
    """Run the launcher and capture its output."""
    return subprocess.run(  # noqa: S603
        ["bash", str(SCRIPT), *args],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )


def test_syntax() -> None:
    """Bash -n passes."""
    assert subprocess.run(["bash", "-n", str(SCRIPT)], check=False).returncode == 0  # noqa: S603, S607


def test_fishing_batches_dry_run_prints_pins_and_command() -> None:
    """Each batch prints pin, harness command and pin, or is refused once its output exists."""
    before = PIN.read_bytes()
    for batch in ("A", "B"):
        out = run("fishing-test", batch, "--dry-run")
        existing = (
            ROOT
            / "harness"
            / "outputs"
            / "experiments"
            / "fishing"
            / "5agents"
            / f"gpt-5.2_endogenous_fishtest{batch}.json"
        )
        if existing.exists():
            assert out.returncode == 3  # noqa: PLR2004
            assert "refusing" in out.stderr
            continue
        assert out.returncode == 0
        lines = [ln for ln in out.stdout.splitlines() if ln.startswith("+ ")]
        assert len(lines) == 3  # noqa: PLR2004
        assert f"model_pin.py before_fishtest{batch}" in lines[0]
        assert "--game fishing --agents 5 --trials 20 --rounds 10 --model gpt-5.2" in lines[1]
        assert f"--run-suffix fishtest{batch}" in lines[1]
        assert f"model_pin.py after_fishtest{batch}" in lines[2]
    assert PIN.read_bytes() == before


def test_bad_batch_and_overwrite_guard() -> None:
    """Unknown batches are rejected, and an existing output file blocks the run."""
    assert run("fishing-test", "C", "--dry-run").returncode == 2  # noqa: PLR2004
    assert run("fishing-test", "A", "--wet").returncode == 2  # noqa: PLR2004
    existing = ROOT / "harness" / "outputs" / "experiments" / "elfarol" / "5agents"
    if (existing / "gpt-5.2_endogenous_main.json").exists():
        out = run("1", "0", "main", "main")
        assert out.returncode == 3  # noqa: PLR2004
        assert "refusing" in out.stderr
