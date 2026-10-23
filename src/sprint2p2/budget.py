"""OpenRouter spend guard."""

import json
import urllib.request

KEY_URL = "https://openrouter.ai/api/v1/key"
CAP_USD = 9.0
COST_PER_CALL_USD = 0.00045


class BudgetError(RuntimeError):
    """Raised when a run would push key usage past the cap."""


def get_usage(api_key: str) -> float:
    """Return the key's cumulative usage in USD from GET /api/v1/key."""
    req = urllib.request.Request(KEY_URL, headers={"Authorization": f"Bearer {api_key}"})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        return float(json.load(resp)["data"]["usage"])


def check_budget(usage: float, n_calls: int, cap: float = CAP_USD) -> float:
    """Return the estimated cost, raising if usage plus the estimate exceeds the cap."""
    estimate = n_calls * COST_PER_CALL_USD
    if usage + estimate > cap:
        msg = f"usage {usage:.2f} + estimate {estimate:.2f} exceeds cap {cap:.2f}"
        raise BudgetError(msg)
    return estimate
