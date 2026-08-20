from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import replace
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
from typing import Iterable

from ..models import (
    Epoch,
    EpochSummary,
    Estimate,
    EstimateStatus,
    Freshness,
    ProviderHealth,
    Sample,
    UsageUnit,
    WindowType,
    datetime_from_text,
    datetime_to_text,
)


class QuotaDatabase:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._initialize()

    def _initialize(self) -> None:
        schema = resources.files("codex_quota_guard.storage").joinpath(
            "schema.sql"
        ).read_text(encoding="utf-8")
        with self._lock, self._connection:
            self._connection.executescript(schema)

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def create_epoch(self, epoch: Epoch) -> Epoch:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                INSERT INTO epochs (
                    window_type, provider, limit_id, started_at, reset_at,
                    duration_minutes, first_percent, last_percent, completed,
                    reset_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    epoch.window_type.value,
                    epoch.provider,
                    epoch.limit_id,
                    datetime_to_text(epoch.started_at),
                    datetime_to_text(epoch.reset_at),
                    epoch.duration_minutes,
                    epoch.first_percent,
                    epoch.last_percent,
                    int(epoch.completed),
                    epoch.reset_reason,
                ),
            )
        return replace(epoch, id=int(cursor.lastrowid))

    def update_epoch_progress(self, epoch_id: int, sample: Sample) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "UPDATE epochs SET last_percent = ?, reset_at = ? WHERE id = ?",
                (sample.used_percent, datetime_to_text(sample.resets_at), epoch_id),
            )

    def complete_epoch(self, epoch: Epoch) -> None:
        if epoch.id is None:
            raise ValueError("Cannot complete an unsaved epoch")
        with self._lock, self._connection:
            self._connection.execute(
                """
                UPDATE epochs
                SET completed = 1, ended_at = ?, last_percent = ?, reset_reason = ?
                WHERE id = ?
                """,
                (
                    datetime_to_text(epoch.ended_at),
                    epoch.last_percent,
                    epoch.reset_reason,
                    epoch.id,
                ),
            )

    def insert_sample(self, epoch_id: int, sample: Sample) -> bool:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                INSERT OR IGNORE INTO samples (
                    epoch_id, timestamp, received_at, window_type, used_percent,
                    reset_at, duration_minutes, cumulative_usage, usage_unit,
                    estimated_credits, cost_usd, input_tokens, cached_input_tokens,
                    output_tokens, model, provider, limit_id, source_signature, stale
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    epoch_id,
                    datetime_to_text(sample.timestamp),
                    datetime_to_text(sample.received_at),
                    sample.window_type.value,
                    sample.used_percent,
                    datetime_to_text(sample.resets_at),
                    sample.duration_minutes,
                    sample.cumulative_usage,
                    sample.usage_unit.value,
                    sample.estimated_credits,
                    sample.cost_usd,
                    sample.input_tokens,
                    sample.cached_input_tokens,
                    sample.output_tokens,
                    sample.model,
                    sample.provider,
                    sample.limit_id,
                    sample.source_signature,
                    int(sample.stale),
                ),
            )
            return cursor.rowcount > 0

    def samples_for_epoch(self, epoch_id: int) -> list[Sample]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM samples WHERE epoch_id = ? ORDER BY timestamp", (epoch_id,)
            ).fetchall()
        return [self._sample_from_row(row) for row in rows]

    def latest_sample(self, epoch_id: int) -> Sample | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM samples WHERE epoch_id = ? ORDER BY timestamp DESC LIMIT 1",
                (epoch_id,),
            ).fetchone()
        return self._sample_from_row(row) if row else None

    def active_epochs(self) -> dict[WindowType, Epoch]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM epochs WHERE completed = 0 ORDER BY started_at"
            ).fetchall()
        return {WindowType(row["window_type"]): self._epoch_from_row(row) for row in rows}

    def save_estimate(self, epoch_id: int, estimate: Estimate) -> None:
        now = datetime.now(timezone.utc)
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO epoch_estimates (
                    epoch_id, calculated_at, status, usage_unit, estimated_total,
                    estimated_used, estimated_remaining, lower_bound, upper_bound,
                    confidence, sample_count, percent_span, residual_mad, warnings
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    epoch_id,
                    datetime_to_text(now),
                    estimate.status.value,
                    estimate.unit.value,
                    estimate.total,
                    estimate.used,
                    estimate.remaining,
                    estimate.lower_bound,
                    estimate.upper_bound,
                    estimate.confidence,
                    estimate.sample_count,
                    estimate.percent_span,
                    estimate.residual_mad,
                    json.dumps(estimate.warnings, ensure_ascii=False),
                ),
            )
            self._connection.execute(
                """
                UPDATE epochs
                SET estimated_total = ?, confidence = ?, lower_bound = ?,
                    upper_bound = ?, usage_unit = ?
                WHERE id = ?
                """,
                (
                    estimate.total,
                    estimate.confidence,
                    estimate.lower_bound,
                    estimate.upper_bound,
                    estimate.unit.value,
                    epoch_id,
                ),
            )

    def completed_estimates(self, window_type: WindowType) -> list[Estimate]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT * FROM epochs
                WHERE completed = 1 AND window_type = ? AND estimated_total IS NOT NULL
                ORDER BY ended_at
                """,
                (window_type.value,),
            ).fetchall()
        estimates: list[Estimate] = []
        for row in rows:
            unit = UsageUnit(row["usage_unit"])
            total = float(row["estimated_total"])
            confidence = int(row["confidence"] or 0)
            estimates.append(
                Estimate(
                    EstimateStatus.READY,
                    unit,
                    total,
                    None,
                    None,
                    row["lower_bound"],
                    row["upper_bound"],
                    confidence,
                    "",
                    0,
                    0.0,
                    None,
                    None,
                    None,
                )
            )
        return estimates

    def list_epochs(self, limit: int = 100) -> list[Epoch]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM epochs ORDER BY started_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._epoch_from_row(row) for row in rows]

    def epoch_summaries(self, limit: int = 100) -> list[EpochSummary]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM epochs ORDER BY started_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            EpochSummary(
                id=int(row["id"]),
                window_type=WindowType(row["window_type"]),
                started_at=datetime_from_text(row["started_at"]),  # type: ignore[arg-type]
                ended_at=datetime_from_text(row["ended_at"]),
                first_percent=float(row["first_percent"]),
                last_percent=float(row["last_percent"]),
                estimated_total=row["estimated_total"],
                confidence=row["confidence"],
                lower_bound=row["lower_bound"],
                upper_bound=row["upper_bound"],
                unit=UsageUnit(row["usage_unit"]),
                completed=bool(row["completed"]),
            )
            for row in rows
        ]

    def set_setting(self, key: str, value: str) -> None:
        now = datetime_to_text(datetime.now(timezone.utc))
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO settings(key, value, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
                """,
                (key, value, now),
            )

    def get_setting(self, key: str) -> str | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            ).fetchone()
        return str(row["value"]) if row else None

    def save_provider_health(self, health: ProviderHealth) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO provider_health (
                    provider, last_success, last_failure, failure_class,
                    consecutive_failures, backoff_until, status, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(provider) DO UPDATE SET
                    last_success=excluded.last_success,
                    last_failure=excluded.last_failure,
                    failure_class=excluded.failure_class,
                    consecutive_failures=excluded.consecutive_failures,
                    backoff_until=excluded.backoff_until,
                    status=excluded.status,
                    error=excluded.error
                """,
                (
                    health.provider,
                    datetime_to_text(health.last_success),
                    datetime_to_text(health.last_failure),
                    health.failure_class,
                    health.consecutive_failures,
                    datetime_to_text(health.backoff_until),
                    health.status.value,
                    health.error,
                ),
            )

    def load_provider_health(self, provider: str) -> ProviderHealth:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM provider_health WHERE provider = ?", (provider,)
            ).fetchone()
        if not row:
            return ProviderHealth(provider)
        return ProviderHealth(
            provider=provider,
            last_success=datetime_from_text(row["last_success"]),
            last_failure=datetime_from_text(row["last_failure"]),
            failure_class=row["failure_class"],
            consecutive_failures=int(row["consecutive_failures"]),
            backoff_until=datetime_from_text(row["backoff_until"]),
            status=Freshness(row["status"]),
            error=row["error"],
        )

    @staticmethod
    def _sample_from_row(row: sqlite3.Row) -> Sample:
        return Sample(
            window_type=WindowType(row["window_type"]),
            timestamp=datetime_from_text(row["timestamp"]),  # type: ignore[arg-type]
            used_percent=float(row["used_percent"]),
            resets_at=datetime_from_text(row["reset_at"]),
            duration_minutes=row["duration_minutes"],
            cumulative_usage=row["cumulative_usage"],
            usage_unit=UsageUnit(row["usage_unit"]),
            provider=row["provider"],
            limit_id=row["limit_id"],
            model=row["model"],
            estimated_credits=row["estimated_credits"],
            cost_usd=row["cost_usd"],
            input_tokens=row["input_tokens"],
            cached_input_tokens=row["cached_input_tokens"],
            output_tokens=row["output_tokens"],
            source_signature=row["source_signature"],
            received_at=datetime_from_text(row["received_at"]),
            stale=bool(row["stale"]),
        )

    @staticmethod
    def _epoch_from_row(row: sqlite3.Row) -> Epoch:
        return Epoch(
            id=int(row["id"]),
            window_type=WindowType(row["window_type"]),
            provider=row["provider"],
            limit_id=row["limit_id"],
            started_at=datetime_from_text(row["started_at"]),  # type: ignore[arg-type]
            reset_at=datetime_from_text(row["reset_at"]),
            duration_minutes=row["duration_minutes"],
            first_percent=float(row["first_percent"]),
            last_percent=float(row["last_percent"]),
            completed=bool(row["completed"]),
            ended_at=datetime_from_text(row["ended_at"]),
            reset_reason=row["reset_reason"],
        )

    def __enter__(self) -> "QuotaDatabase":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
