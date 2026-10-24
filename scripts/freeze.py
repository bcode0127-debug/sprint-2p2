"""Freeze the pre-registration: stamp it, commit it, write configs/frozen.json, push.

Run from the project root, on main, with a clean tree:
    PYTHONPATH=src .venv/bin/python -m scripts.freeze
Do not run it until every blocking PENDING item is settled. osf_url is written empty; fill it in
after the OSF registration, then run scripts/fit_thresholds.py once the threshold split is scored.
"""

import argparse
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from sprint2p2 import analysis, baselines, metrics, scoring

ROOT = Path(__file__).resolve().parent.parent
DRAFT_MARK = "DRAFT, NOT FROZEN"
HASHED = (
    "docs/preregistration.md",
    "prompts/monitor_prompt_v1.txt",
    "configs/monitor.json",
    "src/sprint2p2/views.py",
    "src/sprint2p2/metrics.py",
    "scripts/analyze.py",
)


class FreezeError(RuntimeError):
    """Raised when the repo is not ready to freeze."""


def problems(text: str) -> list[str]:
    """List the reasons a pre-registration text cannot be frozen."""
    found = []
    if "[FILL" in text:
        found.append("contains [FILL")
    for n, line in enumerate(text.splitlines(), start=1):
        if "PENDING" in line and "not blocking" not in line:
            found.append(f"line {n}: blocking PENDING")
    return found


def stamp(text: str, iso: str) -> str:
    """Replace the DRAFT line with the FROZEN line."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if DRAFT_MARK in line:
            lines[i] = f"**FROZEN {iso}**"
            return "\n".join(lines) + "\n"
    msg = f"no '{DRAFT_MARK}' line to replace"
    raise FreezeError(msg)


GIT_STRUCTURAL_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_COMMON_DIR",
    "GIT_PREFIX",
    "GIT_NAMESPACE",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
)


def clean_git_env() -> dict[str, str]:
    """Return the environment without variables that redirect git to another repository.

    Git hooks (and linked worktrees) export these; inheriting them would point git at the
    wrong repository when this module is used from inside a hook or a test run by a hook.
    """
    return {k: v for k, v in os.environ.items() if k not in GIT_STRUCTURAL_VARS}


def git(repo: Path, *args: str) -> str:
    """Run a git command in the repo and return its output."""
    done = subprocess.run(  # noqa: S603
        ["git", "-C", str(repo), *args],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
        env=clean_git_env(),
    )
    return done.stdout.strip()


def file_hashes(repo: Path) -> dict[str, str]:
    """Return the SHA-256 of each frozen file."""
    return {p: analysis.sha256((repo / p).read_text()) for p in HASHED}


def freeze(repo: Path, now: datetime | None = None, *, push: bool = True) -> dict:
    """Run the freeze in the given repo and return the record written to configs/frozen.json."""
    now = now or datetime.now(ZoneInfo("America/New_York"))
    iso = now.isoformat(timespec="seconds")
    prereg = repo / "docs" / "preregistration.md"
    found = problems(prereg.read_text())
    if found:
        msg = "pre-registration is not ready: " + "; ".join(found)
        raise FreezeError(msg)
    if git(repo, "branch", "--show-current") != "main":
        msg = "freeze must run on main"
        raise FreezeError(msg)
    if git(repo, "status", "--porcelain"):
        msg = "working tree is not clean"
        raise FreezeError(msg)
    prereg.write_text(stamp(prereg.read_text(), iso))
    git(repo, "add", "docs/preregistration.md")
    git(repo, "commit", "-q", "-m", f"Freeze pre-registration ({iso})")
    commit = git(repo, "rev-parse", "HEAD")
    pin = json.loads((repo / "results" / "model_pin.json").read_text())[-1]
    record = {
        "prereg_commit": commit,
        "frozen_at": iso,
        "sha256": file_hashes(repo),
        "monitor_model": json.loads((repo / "configs" / "monitor.json").read_text())["model"],
        "agent_model": {"requested": pin["requested"], "resolved": pin["returned_model"]},
        "seeds": {
            "bootstrap_and_threshold_ties": metrics.SEED,
            "random_baseline": baselines.SEED,
            "sampling": scoring.SEED,
        },
        "bootstrap_resamples": metrics.N_BOOT,
        "osf_url": "",
        "thresholds": {},
    }
    (repo / "configs" / "frozen.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n"
    )
    git(repo, "add", "configs/frozen.json")
    git(repo, "commit", "-q", "-m", "Freeze record")
    if push:
        git(repo, "push", "-q", "origin", "main")
    return record


def main() -> None:
    """Command-line entry point."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=str(ROOT))
    ap.add_argument("--no-push", action="store_true")
    args = ap.parse_args()
    record = freeze(Path(args.repo), push=not args.no_push)
    print(f"frozen at {record['prereg_commit']}")  # noqa: T201


if __name__ == "__main__":
    main()
