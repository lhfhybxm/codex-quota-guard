from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable

from ..models import QuotaSnapshot


class QuotaProvider(ABC):
    name: str

    @abstractmethod
    def read(self) -> QuotaSnapshot:
        """Return one normalized, read-only quota snapshot."""

    def set_change_callback(self, callback: Callable[[], None] | None) -> None:
        """Optionally request a refresh after an event-driven provider update."""

    def close(self) -> None:
        """Release local provider resources."""
