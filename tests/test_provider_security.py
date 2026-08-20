from __future__ import annotations

from typing import Any

import pytest

from codex_quota_guard.models import WindowType
from codex_quota_guard.providers.codex_app_server import (
    CodexAppServerProvider,
    parse_account_usage,
    parse_rate_limits,
)
from codex_quota_guard.redaction import redact
from codex_quota_guard.rpc import RpcError
from codex_quota_guard.security import (
    ForbiddenOperationError,
    require_allowed_outgoing_notification,
    require_allowed_request,
)


@pytest.mark.parametrize(
    "method",
    [
        "turn/start",
        "thread/start",
        "responses",
        "v1/chat/completions",
        "account/rateLimitResetCredit/consume",
        "account/logout",
        "account/read",
    ],
)
def test_inference_and_account_writes_are_blocked(method: str) -> None:
    with pytest.raises(ForbiddenOperationError):
        require_allowed_request(method)


def test_only_initialized_can_be_sent_as_notification() -> None:
    require_allowed_outgoing_notification("initialized")
    with pytest.raises(ForbiddenOperationError):
        require_allowed_outgoing_notification("turn/start")


def test_multi_bucket_windows_are_classified_by_duration() -> None:
    payload = {
        "rateLimitsByLimitId": {
            "codex": {
                "limitId": "codex",
                "planType": "plus",
                "primary": {
                    "usedPercent": 12,
                    "windowDurationMins": 300,
                    "resetsAt": 2_000_000_000,
                },
                "secondary": {
                    "usedPercent": 34,
                    "windowDurationMins": 10080,
                    "resetsAt": 2_000_100_000,
                },
                "credits": {"balance": "12.5", "hasCredits": True, "unlimited": False},
            }
        }
    }
    windows, plan, balance, has_credits, unlimited = parse_rate_limits(payload)
    assert windows[WindowType.FIVE_HOUR].used_percent == 12
    assert windows[WindowType.WEEKLY].used_percent == 34
    assert plan == "plus"
    assert balance == "12.5"
    assert has_credits is True and unlimited is False


def test_missing_usage_fields_are_none_not_zero() -> None:
    usage = parse_account_usage({"summary": {}, "dailyUsageBuckets": None})
    assert usage.supported
    assert usage.lifetime_tokens is None
    assert usage.daily_buckets == ()


class FakeTransport:
    notification_callback: Any = None

    def start(self) -> None:
        pass

    def request(self, method: str) -> dict[str, Any]:
        if method == "account/rateLimits/read":
            return {
                "rateLimits": {
                    "limitId": "codex",
                    "primary": {"usedPercent": 5, "windowDurationMins": 300},
                }
            }
        raise RpcError(-32601, "method not supported")

    def close(self) -> None:
        pass


def test_usage_read_unsupported_is_explicit() -> None:
    snapshot = CodexAppServerProvider(FakeTransport()).read()  # type: ignore[arg-type]
    assert snapshot.account_usage.supported is False
    assert snapshot.account_usage.lifetime_tokens is None


def test_sensitive_log_fields_are_redacted() -> None:
    text = redact(
        "Authorization: Bearer secret access_token=abc account_id=acct123 "
        "email=user@example.com cookie=sessionid"
    )
    assert "secret" not in text
    assert "abc" not in text
    assert "acct123" not in text
    assert "user@example.com" not in text
    assert "sessionid" not in text
