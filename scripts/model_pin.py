"""Record the model id that the OpenAI Responses API reports for gpt-5.2."""

import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "model_pin.json"
URL = "https://api.openai.com/v1/responses"


def read_key() -> str:
    """Return OPENAI_API_KEY from .env without echoing it."""
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("OPENAI_API_KEY="):
            return line.split("=", 1)[1].strip()
    msg = "OPENAI_API_KEY missing"
    raise SystemExit(msg)


def main(label: str) -> None:
    """Make one tiny call and append the returned model field to the pin file."""
    body = json.dumps({"model": "gpt-5.2", "input": "hi", "max_output_tokens": 16}).encode()
    req = urllib.request.Request(
        URL,
        data=body,
        headers={"Authorization": f"Bearer {read_key()}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
        returned = json.load(resp)["model"]
    now = datetime.now(ZoneInfo("America/New_York"))
    entries = json.loads(OUT.read_text()) if OUT.exists() else []
    entries.append(
        {
            "label": label,
            "requested": "gpt-5.2",
            "returned_model": returned,
            "timestamp_et": now.isoformat(timespec="seconds"),
        },
    )
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(entries, indent=2) + "\n")
    print(entries[-1])  # noqa: T201


if __name__ == "__main__":
    main(sys.argv[1])
