from __future__ import annotations

from datetime import datetime, timedelta, timezone

from codex_quota_guard.epochs import decide_epoch, new_epoch
from codex_quota_guard.models import Sample, UsageUnit, WindowType
from codex_quota_guard.storage import QuotaDatabase


NOW = datetime(2026, 8, 20, tzinfo=timezone.utc)


def make_sample(percent: float, *, reset_days: int = 7, minute: int = 0) -> Sample:
    return Sample(
        WindowType.WEEKLY,
        NOW + timedelta(minutes=minute),
        percent,
        NOW + timedelta(days=reset_days),
        10080,
        1_000 + 25 * percent,
        UsageUnit.CREDITS,
        "fixture",
        "codex",
        source_signature="v1",
    )


def test_reset_at_change_starts_new_epoch() -> None:
    decision = decide_epoch(make_sample(50), make_sample(51, reset_days=14, minute=1))
    assert decision.starts_new_epoch
    assert decision.reason == "reset_at_changed"


def test_98_to_zero_starts_new_epoch() -> None:
    decision = decide_epoch(make_sample(98), make_sample(0, minute=1))
    assert decision.starts_new_epoch
    assert decision.reason == "percent_wrapped"


def test_old_sample_is_rejected() -> None:
    decision = decide_epoch(make_sample(10, minute=2), make_sample(11, minute=1))
    assert not decision.starts_new_epoch
    assert decision.reason == "old_or_duplicate_sample"


def test_database_restart_restores_epoch_samples_and_schema(tmp_path) -> None:
    path = tmp_path / "quota.db"
    first = make_sample(32)
    with QuotaDatabase(path) as database:
        epoch = database.create_epoch(new_epoch(first, "first_sample"))
        assert epoch.id is not None
        assert database.insert_sample(epoch.id, first)
    with QuotaDatabase(path) as reopened:
        active = reopened.active_epochs()[WindowType.WEEKLY]
        assert active.first_percent == 32
        assert len(reopened.samples_for_epoch(active.id)) == 1
        tables = {
            row[0]
            for row in reopened._connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {
            "samples",
            "epochs",
            "epoch_estimates",
            "settings",
            "model_usage",
            "provider_health",
        } <= tables
