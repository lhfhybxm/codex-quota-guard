# Contributing

Thanks for helping improve Codex Quota Guard. The project has one non-negotiable invariant: observing quota must never create model inference or consume a reset/credit resource.

## Local setup

```powershell
.\scripts\Setup.ps1
.\.venv-win\Scripts\python.exe -m pytest
```

The setup is intentionally project-local and uses Python.org CPython 3.11 on Windows.

## Pull-request rules

- Keep provider output behind the `QuotaProvider` abstraction.
- Add every permitted outbound method to an explicit allowlist and justify it with current official schema evidence.
- Never add prompts, turns, threads, responses, chat completions, credit consumption, or account writes.
- Do not log credentials, cookies, headers, account IDs, emails, raw private responses, or local database contents.
- Preserve `null` for unavailable units; tokens, credits, API-equivalent USD, and subscription price are not interchangeable.
- Add tests for estimator, reset, failure, persistence, and security behavior affected by the change.
- For QML changes, check default, maximized, and 900-pixel-wide layouts on Windows.
- Do not copy implementation code from a project with an incompatible license.

## Suggested checks

```powershell
.\.venv-win\Scripts\python.exe -m compileall -q src tests
.\.venv-win\Scripts\python.exe -m pytest
.\scripts\Build.ps1
```

Do not attach a real account database or unredacted App Server output to an issue or pull request.
