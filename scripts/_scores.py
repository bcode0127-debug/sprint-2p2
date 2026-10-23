"""Shared loading of score files for the analysis scripts."""

from pathlib import Path

from sprint2p2 import analysis, scoring

ROOT = Path(__file__).resolve().parent.parent
SCORES = ROOT / "scores"
DEV_TAG = scoring.DEV_TAG


def load_dir(directory: Path) -> dict[str, dict]:
    """Load every score file in a directory, keyed by scorer name."""
    return {p.stem: scoring.read_rows(p) for p in sorted(directory.glob("*.jsonl"))}


def pick(*, dev_only: bool) -> tuple[dict, dict, str]:
    """Return (threshold rows, test rows, tag); dev-only uses dev for both."""
    if dev_only or not (SCORES / "test" / f"{analysis.PRIMARY_VIEW}.jsonl").exists():
        dev = load_dir(SCORES / "dev")
        return dev, dev, DEV_TAG
    return load_dir(SCORES / "threshold"), load_dir(SCORES / "test"), ""
