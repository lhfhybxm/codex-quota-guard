from __future__ import annotations

import argparse
from pathlib import Path

from .app import default_data_dir, run_gui, run_once


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codex-quota-guard",
        description="Local, zero-inference Codex quota calibration monitor",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=default_data_dir(),
        help="Local SQLite/log directory (default: %%LOCALAPPDATA%%\\CodexQuotaGuard)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Perform one read-only sample and print a sanitized summary",
    )
    parser.add_argument(
        "--no-tray",
        action="store_true",
        help="Show the dashboard without creating a system tray icon",
    )
    parser.add_argument(
        "--start-hidden",
        action="store_true",
        help="Start in the system tray without initially showing the dashboard",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.once:
        return run_once(args.data_dir)
    return run_gui(
        args.data_dir,
        use_tray=not args.no_tray,
        start_hidden=args.start_hidden,
    )


if __name__ == "__main__":
    raise SystemExit(main())
