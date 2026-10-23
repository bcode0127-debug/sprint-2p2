"""Tests for sprint2p2.monitor using a fake network."""

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
