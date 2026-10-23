"""Repo hygiene checks."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = [".env", "harness/", "outputs/", ".venv/"]


def test_gitignore_has_required_entries() -> None:
    """Secrets, harness and outputs must stay untracked."""
    lines = (ROOT / ".gitignore").read_text().split()
    for entry in REQUIRED:
        assert entry in lines
