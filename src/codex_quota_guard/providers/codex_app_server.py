from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from ..models import (
    AccountUsage,
    QuotaSnapshot,
    WindowSnapshot,
    WindowType,
    unix_seconds_to_datetime,
    utc_now,
)
from ..redaction import redact
from ..rpc import AppServerTransport, RpcError
from .base import QuotaProvider


FIVE_HOUR_MINUTES = 300
WEEKLY_MINUTES = 7 * 24 * 60


def _window_type(duration: Any) -> WindowType | None:
    try:
        minutes = int(duration)
    except (TypeError, ValueError):
        return None
    if abs(minutes - FIVE_HOUR_MINUTES) <= 60:
        return WindowType.FIVE_HOUR
    if abs(minutes - WEEKLY_MINUTES) <= 24 * 60:
        return WindowType.WEEKLY
    return None


def _iter_limit_snapshots(payload: dict[str, Any]) -> Iterable[dict[str, Any]]:
    by_id = payload.get("rateLimitsByLimitId")
    if isinstance(by_id, dict) and by_id:
        for key, value in by_id.items():
            if isinstance(value, dict):
                if value.get("limitId") is None:
                    value = dict(value)
                    value["limitId"] = str(key)
                yield value
        return
    legacy = payload.get("rateLimits")
    if isinstance(legacy, dict):
        yield legacy


def parse_rate_limits(payload: dict[str, Any]) -> tuple[
    dict[WindowType, WindowSnapshot], str | None, str | None, bool | None, bool | None
]:
    windows: dict[WindowType, WindowSnapshot] = {}
    plan_type: str | None = None
    balance: str | None = None
    has_credits: bool | None = None
    unlimited: bool | None = None

    snapshots = list(_iter_limit_snapshots(payload))
    if not snapshots and isinstance(payload, dict) and (
        "primary" in payload or "secondary" in payload
    ):
        snapshots = [payload]
    for snapshot in snapshots:
        plan_type = snapshot.get("planType") or plan_type
        credits = snapshot.get("credits")
        if isinstance(credits, dict):
            if credits.get("balance") is not None:
                balance = str(credits["balance"])
            if isinstance(credits.get("hasCredits"), bool):
                has_credits = credits["hasCredits"]
            if isinstance(credits.get("unlimited"), bool):
                unlimited = credits["unlimited"]

        for slot in ("primary", "secondary"):
            raw = snapshot.get(slot)
            if not isinstance(raw, dict):
                continue
            kind = _window_type(raw.get("windowDurationMins"))
            if kind is None:
                continue
            try:
                used_percent = float(raw["usedPercent"])
            except (KeyError, TypeError, ValueError):
                continue
            candidate = WindowSnapshot(
                window_type=kind,
                used_percent=used_percent,
                resets_at=unix_seconds_to_datetime(raw.get("resetsAt")),
                duration_minutes=(
                    int(raw["windowDurationMins"])
                    if raw.get("windowDurationMins") is not None
                    else None
                ),
                limit_id=(
                    str(snapshot["limitId"])
                    if snapshot.get("limitId") is not None
                    else None
                ),
                limit_name=(
                    str(snapshot["limitName"])
                    if snapshot.get("limitName") is not None
                    else None
                ),
            )
            current = windows.get(kind)
            # Prefer the canonical codex bucket, otherwise keep the first stable view.
            if current is None or candidate.limit_id == "codex":
                windows[kind] = candidate
    return windows, plan_type, balance, has_credits, unlimited


def parse_account_usage(payload: dict[str, Any]) -> AccountUsage:
    summary = payload.get("summary")
    lifetime_tokens: int | None = None
    if isinstance(summary, dict) and summary.get("lifetimeTokens") is not None:
        try:
            lifetime_tokens = int(summary["lifetimeTokens"])
        except (TypeError, ValueError):
            lifetime_tokens = None
    buckets: list[tuple[str, int]] = []
    raw_buckets = payload.get("dailyUsageBuckets")
    if isinstance(raw_buckets, list):
        for item in raw_buckets:
            if not isinstance(item, dict):
                continue
            try:
                buckets.append((str(item["startDate"]), int(item["tokens"])))
            except (KeyError, TypeError, ValueError):
                continue
    return AccountUsage(True, lifetime_tokens, tuple(buckets))


class CodexAppServerProvider(QuotaProvider):
    """Provider that reuses Codex login without ever reading credentials."""

    name = "Codex App Server"

    def __init__(
        self,
        transport: AppServerTransport | None = None,
        *,
        source_version: str | None = None,
    ) -> None:
        self._change_callback: Callable[[], None] | None = None
        self._transport = transport or AppServerTransport(
            notification_callback=self._on_notification
        )
        if transport is not None:
            transport.notification_callback = self._on_notification
        self.source_version = source_version

    def set_change_callback(self, callback: Callable[[], None] | None) -> None:
        self._change_callback = callback

    def _on_notification(self, method: str, params: dict[str, Any]) -> None:
        if method == "account/rateLimits/updated" and self._change_callback:
            self._change_callback()

    def read(self) -> QuotaSnapshot:
        self._transport.start()
        rate_payload = self._transport.request("account/rateLimits/read")
        windows, plan_type, balance, has_credits, unlimited = parse_rate_limits(
            rate_payload
        )
        try:
            usage_payload = self._transport.request("account/usage/read")
            usage = parse_account_usage(usage_payload)
        except RpcError as exc:
            usage = AccountUsage(False, error=redact(exc))
        return QuotaSnapshot(
            timestamp=utc_now(),
            provider=self.name,
            windows=windows,
            account_usage=usage,
            plan_type=plan_type,
            purchased_credits_balance=balance,
            has_purchased_credits=has_credits,
            purchased_credits_unlimited=unlimited,
            source_version=self.source_version,
        )

    def close(self) -> None:
        self._transport.close()
