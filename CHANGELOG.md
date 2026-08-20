# Changelog

All notable changes will be documented here. The format follows Keep a Changelog and the project uses semantic versioning.

## [Unreleased]

## [0.1.2] - 2026-08-20

### Added

- Display the weekly remaining percentage as a high-contrast integer inside the tray icon, falling back to the 5-hour window when weekly data is unavailable.
- Show official remaining, used, reset, estimate, source, freshness, and update details in the tray tooltip and menu.

### Changed

- Use `--` instead of inventing a percentage when no official window is available.

## [0.1.1] - 2026-08-20

### Fixed

- Create the ignored `artifacts` parent directory before pytest uses its timestamped temporary path in a clean checkout.
- Report the package version dynamically in the App Server initialization payload.

## [0.1.0] - 2026-08-20

### Added

- Strict read-only Codex App Server transport and deny-by-default RPC policy.
- Separate 5-hour and weekly calibration epochs backed by SQLite.
- Theil–Sen absolute quota estimation, likely ranges, multi-factor confidence, historical baselines, and quota-change detection.
- Single-flight collection, event wakeups, caching, bounded exponential backoff, jitter, and explicit live/stale/unavailable health.
- Native Windows tray behavior and a responsive PySide6/QML dashboard.
- Project-owned Windows icon, deterministic README preview, PyInstaller build, and 34 automated tests.

### Security

- Added credential and identifier redaction.
- Added hard blocks for inference, reset-credit consumption, account writes, and unknown RPC methods.
