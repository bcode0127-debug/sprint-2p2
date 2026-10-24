"""DEV-ONLY PRACTICE scoring with other monitor models (exploration, not a registered result).

Run from the practice worktree root, for example:
    PYTHONPATH=src ../sprint-2p2/.venv/bin/python -m scripts.score_practice --model gemini \
        --views both,actions_only,messages_only
Only the development split is accepted; every other split is refused before any key is read.
"""

import argparse
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from sprint2p2 import monitor, scoring, splits

ROOT = Path(__file__).resolve().parent.parent
TAG = "DEV-ONLY PRACTICE"
MODELS = ("gemini", "sonnet")
MIN_REMAINING_USD = 10.0
RESERVE_USD = 2.0
KEY_URL = "https://openrouter.ai/api/v1/key"
MODELS_URL = "https://openrouter.ai/api/v1/models"


class PracticeError(RuntimeError):
    """Raised when a practice run is asked to touch anything but development data."""


def require_dev(split: str) -> None:
    """Refuse every split except dev."""
    if split != "dev":
        msg = f"practice scoring is DEV-ONLY: split '{split}' refused"
        raise PracticeError(msg)


def read_key() -> str:
    """Return OPENROUTER_API_KEY from .env without echoing it."""
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("OPENROUTER_API_KEY="):
            return line.split("=", 1)[1].strip()
    msg = "OPENROUTER_API_KEY missing"
    raise SystemExit(msg)


def get_json(url: str, key: str) -> dict:
    """GET a JSON document from OpenRouter."""
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})  # noqa: S310
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
        return json.load(resp)


def score_one(case: dict, view: str, runner: scoring.Runner) -> dict:
    """Score one case with the practice monitor and tag the row."""
    row = scoring.score_case(case, view, runner)
    row["tag"] = TAG
    return row


def summarize(rows: list[dict], prices: dict) -> dict:
    """Totals for one view: calls, tokens, parse failures and the estimated cost."""
    prompt = sum(r["prompt_tokens"] for r in rows)
    completion = sum(r["completion_tokens"] for r in rows)
    return {
        "calls": len(rows),
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "reasoning_tokens": sum(r["reasoning_tokens"] for r in rows),
        "parse_failures": sum(not r["parse_ok"] for r in rows),
        "estimated_cost_usd": prompt * prices["prompt"] + completion * prices["completion"],
        "returned_models": sorted({m for r in rows for m in r["models"]}),
    }


def main(argv: list[str] | None = None) -> None:
    """Score the development cases for one practice model."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=MODELS)
    ap.add_argument("--split", default="dev")
    ap.add_argument("--views", required=True)
    ap.add_argument("--sample", type=int, default=0, help="balanced subset size (for probes)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    require_dev(args.split)
    cfg_path = ROOT / "configs" / f"monitor_practice_{args.model}.json"
    cfg = monitor.load_config(cfg_path)
    out = Path(args.out) if args.out else ROOT / "scores" / f"practice_{args.model}_dev"
    logs = splits.load_logs()
    cases = splits.split_cases(logs, "dev")
    if args.sample:
        cases = scoring.sample_balanced(cases, args.sample)
    key = read_key()
    info = get_json(KEY_URL, key)["data"]
    remaining = info["limit"] - info["usage"]
    if remaining < MIN_REMAINING_USD:
        msg = f"HOLD: only {remaining:.2f} USD remaining (needs {MIN_REMAINING_USD:.0f})"
        raise SystemExit(msg)
    listing = {m["id"]: m for m in get_json(MODELS_URL, key)["data"]}[cfg.model]["pricing"]
    prices = {"prompt": float(listing["prompt"]), "completion": float(listing["completion"])}
    print(f"usage before: {info['usage']:.4f}; remaining {remaining:.2f}")  # noqa: T201
    runner = scoring.Runner(logs, cfg, monitor.make_post(key))
    workers = json.loads(cfg_path.read_text())["concurrency"]
    for view in [v for v in args.views.split(",") if v]:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            rows = list(pool.map(lambda c, v=view: score_one(c, v, runner), cases))
        scoring.write_rows(out / f"{view}.jsonl", rows)
        print(view, json.dumps(summarize(rows, prices)))  # noqa: T201


if __name__ == "__main__":
    main()
