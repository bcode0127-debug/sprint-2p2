"""Score a split with the monitor (and optionally the baselines).

Run from the project root with: PYTHONPATH=src .venv/bin/python -m scripts.score_views --split dev
The held-out splits are refused unless configs/frozen.json is complete.
"""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from sprint2p2 import baselines, budget, monitor, scoring, splits, views

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "configs" / "monitor.json"


def read_key() -> str:
    """Return OPENROUTER_API_KEY from .env without echoing it."""
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("OPENROUTER_API_KEY="):
            return line.split("=", 1)[1].strip()
    msg = "OPENROUTER_API_KEY missing"
    raise SystemExit(msg)


def write_baselines(logs: dict, cases: list[dict], fit_split: str, out: Path) -> None:
    """Score and write every baseline for the cases."""
    fit_cases = splits.split_cases(logs, fit_split)
    table = baselines.fit_round_rate(fit_cases)
    scores = baselines.score_all(logs, cases, table)
    for name, values in scores.items():
        rows = [
            {
                "tag": scoring.DEV_TAG if c["split"] == "dev" else "",
                "id": scoring.case_id(c),
                **{
                    k: c[k] for k in ("split", "source", "game", "trial", "round", "agent", "label")
                },
                "view": name,
                "score": v,
                "parse_ok": True,
            }
            for c, v in zip(cases, values, strict=True)
        ]
        scoring.write_rows(out / f"{name}.jsonl", rows)


def main() -> None:
    """Score one split into scores/<split>/<view>.jsonl."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True, choices=["dev", "threshold", "test", "replication"])
    ap.add_argument("--views", default=",".join(views.VIEWS))
    ap.add_argument("--sample", type=int, default=0, help="balanced subset size (dev only)")
    ap.add_argument("--out-root", default=str(ROOT / "scores"))
    ap.add_argument("--baselines", action="store_true")
    ap.add_argument("--rate-fit-split", default="threshold")
    args = ap.parse_args()

    splits.check_gate(args.split)
    logs = splits.load_logs()
    cases = splits.split_cases(logs, args.split)
    if args.sample:
        cases = scoring.sample_balanced(cases, args.sample)
    out = Path(args.out_root) / args.split
    cfg = monitor.load_config(CONFIG)
    workers = json.loads(CONFIG.read_text())["concurrency"]
    if args.baselines:
        write_baselines(logs, cases, args.rate_fit_split, out)
    names = [v for v in args.views.split(",") if v]
    if names:
        key = read_key()
        usage = budget.get_usage(key)
        estimate = budget.check_budget(usage, len(cases) * len(names))
        print(f"usage before: {usage:.4f} USD, estimated this run: {estimate:.2f} USD")  # noqa: T201
        runner = scoring.Runner(logs, cfg, monitor.make_post(key))
        for view in names:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                rows = list(pool.map(lambda c, v=view: scoring.score_case(c, v, runner), cases))
            scoring.write_rows(out / f"{view}.jsonl", rows)


if __name__ == "__main__":
    main()
