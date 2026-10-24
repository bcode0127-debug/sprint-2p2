# ruff: noqa: E501
"""The locked files must hash to the values recorded in Amendment 1 and the freeze record."""

import hashlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
LOCKED = {
    "docs/amendment1.md": "72510f08c4653003ac00040059cfc3e93c826755ff94c644f033049785ce1256",
    "docs/preregistration.md": "a07ea2f7a2be513a06b594f431ae504bb0851f88518e4a048afd73cffaac34e9",
    "configs/monitor.json": "bc6da2d7c5df992bc7ce2423f7b248308e65d5735b96e806a2e6a25acfb5ecb1",
    "prompts/monitor_prompt_v1.txt": "a526d0d078e2056c58f7d6a9a583e176b7dc8b03f30d4b4ac918d4ca54678844",
    "prompts/monitor_prompt_fishing_v1.txt": "56554ad64b0df8ee4712e7bebe86b671cb18b1b8f26511af60ec7018dcec8f75",
    "src/sprint2p2/views.py": "6607cd0f4bb4935325914b7b6e14b98462ca83cd0c3a26bb8b0c21c03934e3f5",
    "src/sprint2p2/metrics.py": "c8b845c061b166ed64503f0042ed40a239ce550734feb910c8218503794acf08",
    "src/sprint2p2/analysis.py": "ee517880765422d90e597555291674e5a1fa80584664e95cd7a4e8ba843a4475",
    "src/sprint2p2/baselines.py": "c4ce6e615854a335d55c025a7cd847a166e6ad287c07e8ad84d6e5df8202ca7d",
    "scripts/analyze.py": "9c4419cfd39122999a97d88dd436daa0000e39565a6b6176e8d20c02e36c3bdd",
}
DATA = {
    "data/raw/elfarol_rep_gpt-5.2.json": "7c2f040a4a59177999243c4e79d2b51ae717306b83d298e1fe4726bff7da3fe7",
    "data/raw/fishing_fishpilot_gpt-5.2.json": "98c42a7489e0023b86baf06110b0bd7f33dd89fae8a996fd4f4006fcd99b8411",
    "data/raw/fishing_pilot_gpt-5.2.json": "24936ea46f065d26964e1f1de0651775e0537a1932fec8d76dfd3c5f5cb3ca59",
}


def sha(rel: str) -> str:
    """Return the SHA-256 of a repo file."""
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


@pytest.mark.parametrize(("rel", "expected"), sorted(LOCKED.items()))
def test_locked_file_hash(rel: str, expected: str) -> None:
    """A locked file changed: Amendment 1 says these are applied unchanged."""
    assert sha(rel) == expected, rel


@pytest.mark.parametrize(("rel", "expected"), sorted(DATA.items()))
def test_raw_data_hash(rel: str, expected: str) -> None:
    """The Amendment 1 raw logs match the recorded checksums."""
    assert sha(rel) == expected, rel
