"""Assemble scores/dev from the cached development runs (no API calls). DEV-ONLY.

Run from the project root with: PYTHONPATH=src .venv/bin/python -m scripts.build_dev_scores
"""

import json
from pathlib import Path

from sprint2p2 import baselines, scoring, splits

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path.home() / "apart-sprint" / "docs" / "run-logs"
RUN1 = ROOT / "results" / "dev_prompt_round.json"
OUT = ROOT / "scores" / "dev"
VIEW_CACHES = (
    "actions_only",
    "messages_only",
    "structured",
    "own_only",
    "freshness",
    "oracle",
    "empty",
    "round_only",
)
KEYS = ("split", "source", "game", "trial", "round", "agent", "label")


def both_rows(cases: list[dict]) -> list[dict]:
    """Rebuild the both rows from run-1 v2 scores and their cached call records."""
    scores = {scoring.case_id(c): c["score_v2"] for c in json.loads(RUN1.read_text())["cases"]}
    calls = json.loads((CACHE / "dev_calls_v2.json").read_text())
    order = [scoring.case_id(c) for c in json.loads(RUN1.read_text())["cases"]]
    call_by_id = dict(zip(order, calls, strict=True))
    rows = []
    for c in cases:
        i = scoring.case_id(c)
        call = call_by_id[i]
        rows.append(
            {
                "tag": scoring.DEV_TAG,
                "id": i,
                **{k: c[k] for k in KEYS},
                "view": "both",
                "score": scores[i],
                "parse_ok": call["parse_ok"],
                "retried": call["retried"],
                "models": call["models"],
                "prompt_tokens": call["prompt_tokens"],
                "completion_tokens": call["completion_tokens"],
                "reasoning_tokens": call["reasoning_tokens"],
            },
        )
    return rows


def main() -> None:
    """Write one score file per view and rule for the 585 development cases."""
    logs = splits.load_logs()
    cases = splits.split_cases(logs, "dev")
    ids = [scoring.case_id(c) for c in cases]
    scoring.write_rows(OUT / "both.jsonl", both_rows(cases))
    for view in VIEW_CACHES:
        by_id = scoring.read_rows(CACHE / f"devall_{view}.jsonl")
        scoring.write_rows(OUT / f"{view}.jsonl", [by_id[i] for i in ids])
    table = baselines.fit_round_rate(cases)
    for name, values in baselines.score_all(logs, cases, table).items():
        rows = [
            {
                "tag": scoring.DEV_TAG,
                "id": i,
                **{k: c[k] for k in KEYS},
                "view": name,
                "score": v,
                "parse_ok": True,
            }
            for i, c, v in zip(ids, cases, values, strict=True)
        ]
        scoring.write_rows(OUT / f"{name}.jsonl", rows)


if __name__ == "__main__":
    main()
