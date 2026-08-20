from __future__ import annotations

import ctypes
import os
from pathlib import Path


_SYSTEM_ICU: object | None = None


def prepare_windows_qt_runtime() -> None:
    """Prevent an Anaconda base runtime from shadowing Windows' ICU shim.

    Qt 6 on Windows links to the stable system ``icuuc.dll`` API. A virtual
    environment created from Anaconda can otherwise make its private ICU DLL
    win the loader search, which has the same filename but incompatible exports.
    """

    global _SYSTEM_ICU
    if os.name != "nt" or _SYSTEM_ICU is not None:
        return
    windows_dir = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    system_icu = windows_dir / "System32" / "icuuc.dll"
    if system_icu.is_file():
        _SYSTEM_ICU = ctypes.WinDLL(str(system_icu))
