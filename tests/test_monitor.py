"""Tests for sprint2p2.monitor using a fake network."""

import json
import urllib.error
from typing import Self

import pytest

from sprint2p2 import monitor

SCALE = 100


def reply(text: str) -> dict:
    """Wrap text in an OpenRouter-shaped response."""
    return {
        "model": "fake/model",
        "choices": [{"message": {"content": text}}],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "completion_tokens_details": {"reasoning_tokens": 0},
        },
    }


def fake_post(texts: list[str]) -> monitor.Post:
    """Return a post function that serves the given texts in order."""
    queue = iter(texts)

    def post(_payload: dict) -> dict:
        return reply(next(queue))

    return post


def test_valid_json() -> None:
    """Plain JSON parses without a retry."""
    res = monitor.monitor_call("p", SCALE, fake_post(['{"probability": 37, "reason": "ok."}']))
    assert (res.score, res.parse_ok, res.retried) == (37, True, False)


def test_fenced_json() -> None:
    """Fenced JSON parses."""
    text = '```json\n{"probability": 80, "reason": "x"}\n```'
    res = monitor.monitor_call("p", SCALE, fake_post([text]))
    assert (res.score, res.parse_ok) == (80, True)


def test_garbage_then_retry() -> None:
    """Garbage triggers one retry, whose tokens are also counted."""
    texts = ["no idea", '{"probability": 12, "reason": "r"}']
    res = monitor.monitor_call("p", SCALE, fake_post(texts))
    assert (res.score, res.parse_ok, res.retried) == (12, True, True)
    assert res.prompt_tokens == 2 * 10


def test_garbage_twice_fails() -> None:
    """Two failures leave parse_ok false."""
    res = monitor.monitor_call("p", SCALE, fake_post(["x", "y"]))
    assert res.score is None
    assert not res.parse_ok


def test_truncated_and_out_of_range() -> None:
    """Truncated JSON still yields the leading probability; out of range does not."""
    assert monitor.parse_probability('{"probability": 55, "reason": "cut', SCALE)[0] == 55  # noqa: PLR2004
    assert monitor.parse_probability('{"probability": 150}', SCALE)[0] is None


def test_prompt_scales_differ_only_in_scale() -> None:
    """The two prompt variants differ only where SCALE appears."""
    a = monitor.render_prompt("J", 3, "REC", 100)
    b = monitor.render_prompt("J", 3, "REC", 1000)
    assert a != b
    assert a.replace("0 to 100", "0 to X") == b.replace("0 to 1000", "0 to X")


def test_request_disables_reasoning() -> None:
    """The payload carries reasoning disabled, temperature 0 and max_tokens 150."""
    seen: list[dict] = []

    def post(payload: dict) -> dict:
        seen.append(payload)
        return reply('{"probability": 1, "reason": "r"}')

    res = monitor.monitor_call("p", SCALE, post)
    assert seen[0]["reasoning"] == {"enabled": False}
    assert (seen[0]["temperature"], seen[0]["max_tokens"]) == (0, 150)
    assert res.reasoning_tokens == 0


def test_v1_prompt_has_no_round_number() -> None:
    """The v1 task text says 'this round' and carries no round number or SCALE slot."""
    text = monitor.render_prompt("J", 7, "REC", 100, "monitor_prompt_v1.txt")
    assert "7" not in text.replace("100", "").replace("+10", "").replace("-5", "")
    assert "this round" in text
    assert "privately plans" in text
    assert "REC" in text


def test_v2_payload() -> None:
    """v2 sets reasoning max_tokens 1024, max_tokens 1500 and omits temperature."""
    seen: list[dict] = []

    def post(payload: dict) -> dict:
        seen.append(payload)
        return reply('{"probability": 1, "reason": "r"}')

    monitor.monitor_call("p", SCALE, post, monitor.VARIANTS["v2"])
    assert seen[0]["reasoning"] == {"max_tokens": 1024}
    assert seen[0]["max_tokens"] == 1500  # noqa: PLR2004
    assert "temperature" not in seen[0]


class FakeResponse:
    """Minimal context-manager response for the fake opener."""

    def __init__(self, body: dict) -> None:
        """Hold the JSON body."""
        self.body = json.dumps(body).encode()

    def __enter__(self) -> Self:
        """Enter the context."""
        return self

    def __exit__(self, *_exc: object) -> None:
        """Leave the context."""

    def read(self) -> bytes:
        """Return the body bytes."""
        return self.body


def http_error(code: int) -> urllib.error.HTTPError:
    """Build an HTTPError with the given status."""
    return urllib.error.HTTPError("u", code, "m", {}, None)  # type: ignore[arg-type]


def test_backoff_retries_then_succeeds() -> None:
    """Two 429s then success sleeps 1s then 2s."""
    outcomes = [http_error(429), http_error(503), FakeResponse({"ok": 1})]
    sleeps: list[float] = []

    def opener(_req: object, timeout: int) -> FakeResponse:  # noqa: ARG001
        out = outcomes.pop(0)
        if isinstance(out, Exception):
            raise out
        return out

    post = monitor.make_post("k", opener, sleeps.append)
    assert post({}) == {"ok": 1}
    assert sleeps == [1.0, 2.0]


def test_backoff_gives_up_and_skips_non_retryable() -> None:
    """A 400 is raised at once; repeated 429s raise after the last attempt."""
    sleeps: list[float] = []

    def bad_request(_req: object, timeout: int) -> None:  # noqa: ARG001
        raise http_error(400)

    with pytest.raises(urllib.error.HTTPError):
        monitor.make_post("k", bad_request, sleeps.append)({})
    assert sleeps == []

    def always_429(_req: object, timeout: int) -> None:  # noqa: ARG001
        raise http_error(429)

    with pytest.raises(urllib.error.HTTPError):
        monitor.make_post("k", always_429, sleeps.append)({})
    assert sleeps == [1.0, 2.0, 4.0, 8.0]


def test_load_config() -> None:
    """configs/monitor.json is the v2 setting."""
    cfg = monitor.load_config()
    assert cfg.model == "anthropic/claude-haiku-5.5"
    assert cfg.template == "monitor_prompt_v1.txt"
    assert (cfg.scale, cfg.max_tokens, cfg.temperature) == (100, 1500, None)
    assert cfg.reasoning == {"max_tokens": 1024}
    assert cfg == monitor.VARIANTS["v2"]
