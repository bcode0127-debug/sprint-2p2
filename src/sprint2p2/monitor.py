"""OpenRouter monitor call with a forgiving JSON parser."""

import json
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "anthropic/claude-haiku-5.5"
PROMPT_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"
_FENCE = re.compile(r"```(?:json)?", re.IGNORECASE)
_OBJECT = re.compile(r"\{.*\}", re.DOTALL)
_PROB = re.compile(r"\"?probability\"?\s*[:=]\s*(-?\d+(?:\.\d+)?)", re.IGNORECASE)

Post = Callable[[dict], dict]


@dataclass(frozen=True)
class Config:
    """Prompt template and request settings for one monitor variant."""

    template: str
    reasoning: dict
    max_tokens: int
    temperature: float | None
    model: str = MODEL
    scale: int = 100


RETRY_CODES = (429, 500, 502, 503, 504)
ATTEMPTS = 5
BASE_DELAY_S = 1.0
CONFIG_PATH = PROMPT_DIR.parent / "configs" / "monitor.json"


def load_config(path: Path = CONFIG_PATH) -> Config:
    """Read the monitor settings from a JSON config file."""
    raw = json.loads(path.read_text())
    return Config(
        template=Path(raw["prompt"]).name,
        reasoning=raw["reasoning"],
        max_tokens=raw["max_tokens"],
        temperature=raw.get("temperature"),
        model=raw["model"],
        scale=raw["scale"]["max"],
    )


VARIANTS = {
    "v0": Config("monitor_prompt_v0.txt", {"enabled": False}, 150, 0),
    "v1": Config("monitor_prompt_v1.txt", {"enabled": False}, 150, 0),
    "v2": Config("monitor_prompt_v1.txt", {"max_tokens": 1024}, 1500, None),
}


@dataclass
class MonitorResult:
    """Outcome of one monitored case."""

    score: int | None
    reason: str | None
    parse_ok: bool
    retried: bool
    models: list[str] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0
    error: str | None = None


def render_prompt(
    agent: str,
    round_r: int,
    record: str,
    scale: int,
    template: str = "monitor_prompt_v0.txt",
) -> str:
    """Fill the prompt template; only SCALE differs between variants."""
    text = (PROMPT_DIR / template).read_text(encoding="utf-8")
    return text.format(AGENT=agent, R=round_r, RECORD=record, SCALE=scale)


def parse_probability(text: str, scale: int) -> tuple[int | None, str | None]:
    """Extract an integer probability in [0, scale] from model text, or None."""
    cleaned = _FENCE.sub("", text)
    value, reason = None, None
    match = _OBJECT.search(cleaned)
    if match:
        try:
            obj = json.loads(match.group(0))
            value, reason = obj.get("probability"), obj.get("reason")
        except (json.JSONDecodeError, AttributeError):
            value = None
    if value is None:
        fallback = _PROB.search(cleaned)
        value = float(fallback.group(1)) if fallback else None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None, None
    score = round(value)
    if not 0 <= score <= scale:
        return None, None
    return score, reason if isinstance(reason, str) else None


def make_post(
    api_key: str,
    opener: Callable = urllib.request.urlopen,
    sleep: Callable = time.sleep,
) -> Post:
    """Return a function that posts to OpenRouter, retrying with exponential backoff."""

    def post(payload: dict) -> dict:
        req = urllib.request.Request(
            URL,
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )
        for attempt in range(ATTEMPTS):
            try:
                with opener(req, timeout=90) as resp:
                    return json.load(resp)
            except urllib.error.HTTPError as exc:
                if exc.code not in RETRY_CODES or attempt == ATTEMPTS - 1:
                    raise
            except (urllib.error.URLError, TimeoutError):
                if attempt == ATTEMPTS - 1:
                    raise
            sleep(BASE_DELAY_S * 2**attempt)
        msg = "unreachable"
        raise RuntimeError(msg)

    return post


def monitor_call(
    prompt: str,
    scale: int,
    post: Post,
    cfg: Config = VARIANTS["v0"],
) -> MonitorResult:
    """Call the monitor, retrying once on a parse failure or transport error."""
    result = MonitorResult(None, None, parse_ok=False, retried=False)
    payload = {
        "model": cfg.model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": cfg.max_tokens,
        "reasoning": cfg.reasoning,
    }
    if cfg.temperature is not None:
        payload["temperature"] = cfg.temperature
    for attempt in range(2):
        result.retried = attempt == 1
        try:
            resp = post(payload)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            result.error = type(exc).__name__
            continue
        usage = resp.get("usage") or {}
        result.prompt_tokens += usage.get("prompt_tokens", 0)
        result.completion_tokens += usage.get("completion_tokens", 0)
        details = usage.get("completion_tokens_details") or {}
        result.reasoning_tokens += details.get("reasoning_tokens") or 0
        result.models.append(str(resp.get("model")))
        choices = resp.get("choices") or [{}]
        text = (choices[0].get("message") or {}).get("content") or ""
        result.score, result.reason = parse_probability(text, scale)
        if result.score is not None:
            result.parse_ok = True
            result.error = None
            break
        result.error = "parse_failure"
    return result
