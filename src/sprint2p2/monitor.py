"""OpenRouter monitor call with a forgiving JSON parser."""

import json
import re
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "anthropic/claude-haiku-5.5"
MAX_TOKENS = 150
REASONING = {"enabled": False}
PROMPT_PATH = Path(__file__).resolve().parent.parent.parent / "prompts" / "monitor_prompt_v0.txt"
_FENCE = re.compile(r"```(?:json)?", re.IGNORECASE)
_OBJECT = re.compile(r"\{.*\}", re.DOTALL)
_PROB = re.compile(r"\"?probability\"?\s*[:=]\s*(-?\d+(?:\.\d+)?)", re.IGNORECASE)

Post = Callable[[dict], dict]


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


def render_prompt(agent: str, round_r: int, record: str, scale: int) -> str:
    """Fill the prompt template; only SCALE differs between variants."""
    template = PROMPT_PATH.read_text()
    return template.format(AGENT=agent, R=round_r, RECORD=record, SCALE=scale)


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


def make_post(api_key: str) -> Post:
    """Return a function that posts one chat completion to OpenRouter."""

    def post(payload: dict) -> dict:
        req = urllib.request.Request(
            URL,
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=90) as resp:  # noqa: S310
            return json.load(resp)

    return post


def monitor_call(prompt: str, scale: int, post: Post) -> MonitorResult:
    """Call the monitor, retrying once on a parse failure or transport error."""
    result = MonitorResult(None, None, parse_ok=False, retried=False)
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": MAX_TOKENS,
        "reasoning": REASONING,
    }
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
