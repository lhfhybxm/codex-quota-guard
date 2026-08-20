from __future__ import annotations

import re


_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"(?i)\b(authorization)\s*[:=]\s*(?:bearer\s+)?[^\s,;]+"),
        r"\1=[REDACTED]",
    ),
    (
        re.compile(r"(?i)\b(access[_-]?token|refresh[_-]?token|id[_-]?token)\s*[:=]\s*[^\s,;]+"),
        r"\1=[REDACTED]",
    ),
    (
        re.compile(r"(?i)\b(cookie|set-cookie)\s*[:=]\s*[^\r\n]+"),
        r"\1=[REDACTED]",
    ),
    (
        re.compile(r"(?i)\b(account[_-]?id|user[_-]?id)\s*[:=]\s*[\w.@:+/-]+"),
        r"\1=[REDACTED]",
    ),
    (
        re.compile(r"(?i)\b(email)\s*[:=]\s*[^\s,;]+"),
        r"\1=[REDACTED]",
    ),
    (
        re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
        "[REDACTED_EMAIL]",
    ),
    (
        re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]+=*"),
        "Bearer [REDACTED]",
    ),
)


def redact(value: object, *, max_length: int = 600) -> str:
    text = str(value)
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    if len(text) > max_length:
        return text[:max_length] + "…"
    return text
