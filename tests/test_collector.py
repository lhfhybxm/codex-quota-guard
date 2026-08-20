from __future__ import annotations

import random
import threading
from datetime import datetime, timedelta, timezone

import pytest

from codex_quota_guard.collector import (
    ExponentialBackoff,
    SnapshotCollector,
    classify_failure,
)
from codex_quota_guard.models import AccountUsage, QuotaSnapshot, WindowSnapshot, WindowType
from codex_quota_guard.providers.base import QuotaProvider
from codex_quota_guard.rpc import RpcError
from codex_quota_guard.storage import QuotaDatabase


NOW = datetime(2026, 8, 20, tzinfo=timezone.utc)


class RecoveringProvider(QuotaProvider):
    name = "fixture"

    def __init__(self, *, block: threading.Event | None = None) -> None:
        self.calls = 0
        self.block = block
        self.callback = None

    def set_change_callback(self, callback):
        self.callback = callback

    def read(self) -> QuotaSnapshot:
        self.calls += 1
        if self.block:
            self.block.wait(2)
        if self.calls == 1 and self.block is None:
            raise ConnectionError("offline")
        return QuotaSnapshot(
            NOW + timedelta(minutes=self.calls),
            self.name,
            {
                WindowType.WEEKLY: WindowSnapshot(
                    WindowType.WEEKLY,
                    10 + self.calls,
                    NOW + timedelta(days=7),
                    10080,
                    "codex",
                )
            },
            AccountUsage(True, 10_000 + self.calls * 100),
            source_version="test",
        )


def test_network_failure_recovers_on_next_refresh(tmp_path) -> None:
    provider = RecoveringProvider()
    with QuotaDatabase(tmp_path / "quota.db") as database:
        collector = SnapshotCollector(provider, database, clock=lambda: NOW)
        first = collector.refresh(force=True)
        assert first.error
        assert first.health.failure_class == "network"
        second = collector.refresh(force=True)
        assert second.snapshot is not None
        assert second.health.consecutive_failures == 0


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (RpcError(401, "unauthorized"), "authentication"),
        (RpcError(403, "forbidden"), "authentication"),
        (RpcError(429, "rate limit"), "rate_limited"),
        (RpcError(500, "server"), "server_error"),
    ],
)
def test_future_wham_style_statuses_are_classified(error, expected) -> None:
    assert classify_failure(error) == expected


def test_backoff_is_bounded_and_retry_after_wins() -> None:
    backoff = ExponentialBackoff(random_source=random.Random(0), jitter_ratio=0)
    assert backoff.delay(1) == 15
    assert backoff.delay(3) == 60
    assert backoff.delay(99) == 900
    assert backoff.delay(4, retry_after_seconds=123) == 123


def test_concurrent_refresh_is_single_flight(tmp_path) -> None:
    gate = threading.Event()
    provider = RecoveringProvider(block=gate)
    with QuotaDatabase(tmp_path / "quota.db") as database:
        collector = SnapshotCollector(provider, database, clock=lambda: NOW)
        results = []
        threads = [
            threading.Thread(target=lambda: results.append(collector.refresh(force=True)))
            for _ in range(2)
        ]
        for thread in threads:
            thread.start()
        gate.set()
        for thread in threads:
            thread.join(3)
        assert provider.calls == 1
        assert len(results) == 2
