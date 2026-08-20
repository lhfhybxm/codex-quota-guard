from __future__ import annotations


class ForbiddenOperationError(RuntimeError):
    """Raised before any non-read-only RPC can reach the transport."""


ALLOWED_REQUEST_METHODS = frozenset(
    {
        "initialize",
        "account/rateLimits/read",
        "account/usage/read",
    }
)
ALLOWED_OUTGOING_NOTIFICATIONS = frozenset({"initialized"})
ALLOWED_INCOMING_NOTIFICATIONS = frozenset({"account/rateLimits/updated"})


def require_allowed_request(method: str) -> None:
    if method not in ALLOWED_REQUEST_METHODS:
        raise ForbiddenOperationError(
            f"Operation is not on the read-only quota allowlist: {method!r}"
        )


def require_allowed_outgoing_notification(method: str) -> None:
    if method not in ALLOWED_OUTGOING_NOTIFICATIONS:
        raise ForbiddenOperationError(
            f"Notification is not on the read-only quota allowlist: {method!r}"
        )


def is_allowed_incoming_notification(method: str) -> bool:
    return method in ALLOWED_INCOMING_NOTIFICATIONS
