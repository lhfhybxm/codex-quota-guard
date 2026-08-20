from __future__ import annotations

from datetime import datetime

from ..models import Estimate, EstimateStatus, UsageUnit


UNIT_LABELS = {
    UsageUnit.CREDITS: "credits",
    UsageUnit.TOKENS: "tokens",
    UsageUnit.API_USD: "API-equivalent USD",
    UsageUnit.UNKNOWN: "units unavailable",
}


def format_number(value: float | int | None) -> str:
    if value is None:
        return "—"
    if abs(float(value)) >= 100:
        return f"{value:,.0f}"
    return f"{value:,.1f}"


def format_compact_number(value: float | int | None) -> str:
    if value is None:
        return "—"
    number = float(value)
    magnitude = abs(number)
    if magnitude >= 1_000_000:
        compact = f"{number / 1_000_000:.2f}".rstrip("0").rstrip(".")
        return f"{compact}M"
    if magnitude >= 100_000:
        return f"{number / 1_000:.0f}K"
    if magnitude >= 10_000:
        compact = f"{number / 1_000:.1f}".rstrip("0").rstrip(".")
        return f"{compact}K"
    return format_number(value)


def format_reset(value: datetime | None, weekly: bool = False) -> str:
    if value is None:
        return "unknown"
    local = value.astimezone()
    return local.strftime("%Y-%m-%d %H:%M") if weekly else local.strftime("%H:%M")


def estimate_lines(estimate: Estimate | None) -> tuple[str, str, str, str]:
    if estimate is None or estimate.status is EstimateStatus.UNAVAILABLE:
        reason = estimate.reason if estimate else "Waiting for a valid sample"
        return ("Absolute estimate unavailable", reason or "", "", "")
    if estimate.status is EstimateStatus.WARMING_UP:
        return (
            "正在校准 / Calibrating",
            "至少需要约 5% 的有效使用跨度",
            f"Observed span: {estimate.percent_span:.1f}%",
            "",
        )
    unit = UNIT_LABELS[estimate.unit]
    return (
        f"Estimated total: ~{format_number(estimate.total)} {unit}",
        f"Estimated used: ~{format_number(estimate.used)} {unit}",
        f"Estimated remaining: ~{format_number(estimate.remaining)} {unit}",
        (
            f"Likely range: {format_number(estimate.lower_bound)} – "
            f"{format_number(estimate.upper_bound)} {unit} · "
            f"Confidence {estimate.confidence}% ({estimate.confidence_label})"
        ),
    )
