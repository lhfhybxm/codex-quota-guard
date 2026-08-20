from __future__ import annotations

import random
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Callable

from .epochs import complete_epoch, decide_epoch, new_epoch
from .estimator import estimate_quota
from .models import (
    CollectionResult,
    Estimate,
    Freshness,
    ProviderHealth,
    QuotaSnapshot,
    Sample,
    UsageUnit,
    WindowType,
)
from .providers.base import QuotaProvider
from .redaction import redact
from .rpc import RpcError, RpcTimeoutError
from .storage import QuotaDatabase


DEFAULT_POLL_SECONDS = 4 * 60


def classify_failure(error: BaseException) -> str:
    text = str(error).lower()
    if isinstance(error, RpcTimeoutError) or "timeout" in text or "timed out" in text:
        return "timeout"
    if isinstance(error, RpcError):
        code = str(error.code).lower()
        if code in {"401", "403"} or "unauthorized" in text or "forbidden" in text:
            return "authentication"
        if code == "429" or "rate limit" in text:
            return "rate_limited"
        if code in {"-32601", "method_not_found"} or "not supported" in text:
            return "unsupported"
        if code.startswith("5"):
            return "server_error"
        if code == "malformed":
            return "malformed_response"
    if isinstance(error, (ConnectionError, OSError)):
        return "network"
    return "unknown"


class ExponentialBackoff:
    def __init__(
        self,
        *,
        base_seconds: float = 15.0,
        cap_seconds: float = 15 * 60.0,
        jitter_ratio: float = 0.20,
        random_source: random.Random | None = None,
    ) -> None:
        self.base_seconds = base_seconds
        self.cap_seconds = cap_seconds
        self.jitter_ratio = jitter_ratio
        self.random = random_source or random.Random()

    def delay(self, failures: int, retry_after_seconds: float | None = None) -> float:
        if retry_after_seconds is not None:
            return max(0.0, retry_after_seconds)
        raw = min(self.cap_seconds, self.base_seconds * (2 ** max(0, failures - 1)))
        jitter = raw * self.jitter_ratio
        return max(0.0, raw + self.random.uniform(-jitter, jitter))


class SnapshotCollector:
    """Single-flight, persistent collector shared by timer, event, and UI refresh."""

    def __init__(
        self,
        provider: QuotaProvider,
        database: QuotaDatabase,
        *,
        poll_seconds: float = DEFAULT_POLL_SECONDS,
        cache_seconds: float = 30.0,
        stale_after_seconds: float = 12 * 60.0,
        clock: Callable[[], datetime] | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        backoff: ExponentialBackoff | None = None,
    ) -> None:
        self.provider = provider
        self.database = database
        self.poll_seconds = poll_seconds
        self.cache_seconds = cache_seconds
        self.stale_after_seconds = stale_after_seconds
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.monotonic = monotonic
        self.backoff = backoff or ExponentialBackoff()
        self.health = database.load_provider_health(provider.name)
        self._active_epochs = database.active_epochs()
        self._condition = threading.Condition()
        self._in_flight = False
        self._last_result: CollectionResult | None = None
        self._last_result_monotonic: float | None = None
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._listeners: list[Callable[[CollectionResult], None]] = []
        self.provider.set_change_callback(self._on_provider_change)

    def add_listener(self, listener: Callable[[CollectionResult], None]) -> None:
        self._listeners.append(listener)

    def _on_provider_change(self) -> None:
        self._wake.set()

    def refresh(self, *, force: bool = False) -> CollectionResult:
        with self._condition:
            if (
                not force
                and self._last_result is not None
                and self._last_result_monotonic is not None
                and self.monotonic() - self._last_result_monotonic < self.cache_seconds
            ):
                return self._last_result
            if self._in_flight:
                self._condition.wait_for(lambda: not self._in_flight)
                if self._last_result is not None:
                    return self._last_result
            self._in_flight = True

        try:
            result = self._collect_once()
        except Exception as exc:
            result = self._record_failure(exc)
        with self._condition:
            self._last_result = result
            self._last_result_monotonic = self.monotonic()
            self._in_flight = False
            self._condition.notify_all()
        for listener in tuple(self._listeners):
            try:
                listener(result)
            except Exception:
                pass
        return result

    def _collect_once(self) -> CollectionResult:
        snapshot = self.provider.read()
        samples: list[Sample] = []
        estimates: dict[WindowType, Estimate] = {}
        now = self.clock()
        cumulative = snapshot.account_usage.lifetime_tokens
        usage_unit = UsageUnit.TOKENS if cumulative is not None else UsageUnit.UNKNOWN

        for window_type, window in snapshot.windows.items():
            sample = Sample(
                window_type=window_type,
                timestamp=snapshot.timestamp,
                received_at=now,
                used_percent=window.used_percent,
                resets_at=window.resets_at,
                duration_minutes=window.duration_minutes,
                cumulative_usage=float(cumulative) if cumulative is not None else None,
                usage_unit=usage_unit,
                provider=snapshot.provider,
                limit_id=window.limit_id,
                source_signature=(
                    f"{snapshot.provider}|{snapshot.source_version or 'unknown'}|"
                    f"{window.limit_id or 'default'}"
                ),
            )
            epoch = self._active_epochs.get(window_type)
            previous = self.database.latest_sample(epoch.id) if epoch and epoch.id else None
            decision = decide_epoch(previous, sample)
            if decision.reason == "old_or_duplicate_sample":
                continue
            if epoch is None or decision.starts_new_epoch:
                if epoch is not None:
                    epoch.last_percent = previous.used_percent if previous else epoch.last_percent
                    complete_epoch(epoch, sample.timestamp, decision.reason or "new_epoch")
                    self.database.complete_epoch(epoch)
                epoch = self.database.create_epoch(
                    new_epoch(sample, decision.reason or "first_sample")
                )
                self._active_epochs[window_type] = epoch
            if epoch.id is None:
                continue
            inserted = self.database.insert_sample(epoch.id, sample)
            if not inserted:
                continue
            epoch.last_percent = sample.used_percent
            epoch.reset_at = sample.resets_at
            self.database.update_epoch_progress(epoch.id, sample)
            epoch_samples = self.database.samples_for_epoch(epoch.id)
            estimate = estimate_quota(
                epoch_samples, now=now, stale_after_seconds=self.stale_after_seconds
            )
            self.database.save_estimate(epoch.id, estimate)
            samples.append(sample)
            estimates[window_type] = estimate

        self.health.last_success = now
        self.health.failure_class = None
        self.health.consecutive_failures = 0
        self.health.backoff_until = None
        self.health.status = Freshness.LIVE
        self.health.error = None
        self.database.save_provider_health(self.health)
        return CollectionResult(snapshot, tuple(samples), estimates, self.health)

    def _record_failure(self, error: BaseException) -> CollectionResult:
        now = self.clock()
        failure_class = classify_failure(error)
        self.health.last_failure = now
        self.health.failure_class = failure_class
        self.health.consecutive_failures += 1
        retry_after = error.retry_after_seconds if isinstance(error, RpcError) else None
        delay = self.backoff.delay(self.health.consecutive_failures, retry_after)
        self.health.backoff_until = now + timedelta(seconds=delay)
        self.health.error = redact(error)
        if self.health.last_success is None:
            self.health.status = Freshness.UNAVAILABLE
        elif (now - self.health.last_success).total_seconds() >= self.stale_after_seconds:
            self.health.status = Freshness.UNAVAILABLE
        else:
            self.health.status = Freshness.STALE
        self.database.save_provider_health(self.health)
        return CollectionResult(
            self._last_result.snapshot if self._last_result else None,
            estimates=(self._last_result.estimates if self._last_result else {}),
            health=self.health,
            error=redact(error),
        )

    def run(self) -> None:
        while not self._stop.is_set():
            self.refresh(force=True)
            delay = self.poll_seconds
            if self.health.backoff_until is not None:
                delay = max(1.0, (self.health.backoff_until - self.clock()).total_seconds())
            self._wake.wait(delay)
            self._wake.clear()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        self.provider.close()
