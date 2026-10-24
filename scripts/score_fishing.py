"""Score Fishing cases with the monitor (Amendment 1, section 4).

Views: both, actions_only, oracle, empty. Run from the project root:
    PYTHONPATH=src .venv/bin/python -m scripts.score_fishing --split fishing_dev
The fishing_test split is refused unless configs/frozen.json holds amendment1_url (and the freeze,
OSF link and thresholds) and both batch logs (fishtestA and fishtestB) exist, so no batch is scored
before the other has been generated.
"""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from scripts.score_views import CONFIG, read_key
from sprint2p2 import budget, fishing, monitor, scoring, splits

ROOT = Path(__file__).resolve().parent.parent
VIEWS = fishing.FISHING_VIEWS


def load_inputs(split: str) -> tuple[dict[str, dict], list[dict]]:
    """Gate the split, load its raw logs and list its cases."""
    splits.check_gate(split)
    if split == "fishing_test":
        logs = fishing.load_test_logs()
    else:
        logs = {"fishpilot": json.loads(splits.FISHING_PILOT_RAW.read_text(encoding="utf-8"))}
    cases = []
    for source, log in logs.items():
        cases += fishing.fishing_cases(log, source, split=split)
    return logs, cases


def main(argv: list[str] | None = None) -> None:
    """Score one Fishing split into scores/<split>/<view>.jsonl."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True, choices=["fishing_dev", "fishing_test"])
    ap.add_argument("--views", default=",".join(VIEWS))
    ap.add_argument("--out-root", default=str(ROOT / "scores"))
    args = ap.parse_args(argv)
    logs, cases = load_inputs(args.split)
    names = [v for v in args.views.split(",") if v]
    key = read_key()
    usage = budget.get_usage(key)
    estimate = budget.check_budget(usage, len(cases) * len(names))
    print(f"usage before: {usage:.4f} USD, estimated this run: {estimate:.2f} USD")  # noqa: T201
    runner = scoring.Runner(logs, monitor.load_config(CONFIG), monitor.make_post(key))
    workers = json.loads(CONFIG.read_text())["concurrency"]
    for view in names:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            rows = list(pool.map(lambda c, v=view: fishing.score_case(c, v, runner), cases))
        scoring.write_rows(Path(args.out_root) / args.split / f"{view}.jsonl", rows)


if __name__ == "__main__":
    main()
