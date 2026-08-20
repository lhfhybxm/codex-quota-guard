# Privacy and security

## RPC policy

The security policy is a positive allowlist evaluated before bytes reach the App Server transport.

Allowed requests:

```text
initialize
account/rateLimits/read
account/usage/read
```

Allowed outbound notification:

```text
initialized
```

Accepted incoming notification:

```text
account/rateLimits/updated
```

Every other request or notification fails closed. Tests explicitly cover `turn/start`, `thread/start`, Responses, Chat Completions, reset-credit consumption, logout/account writes, and unknown methods.

## Credentials

The project launches the local Codex App Server and relies on Codex's existing login. It does not parse Codex auth files, request copied access tokens, intercept browser cookies, or transmit credentials to another service.

## Local data

The default directory is `%LOCALAPPDATA%\CodexQuotaGuard`. It contains:

- `quota.db`: percentages, reset times, typed usage counters, estimates, and provider health;
- `app.log`: operational diagnostics after redaction.

The application has no telemetry client, analytics SDK, crash uploader, update service, web server, or cloud database.

## Redaction

Before errors are logged or surfaced, the redactor targets access/refresh tokens, bearer authorization, cookies, account/user IDs, email addresses, and common secret-bearing JSON fields. App Server stderr is logged only at debug level after redaction.

Redaction is defense in depth, not permission to log sensitive responses. Providers should retain only normalized fields needed for estimation.

## Private endpoints

`https://chatgpt.com/backend-api/wham/usage` is not an active provider in v0.1.0. It is a private interface whose authentication and stability are not guaranteed. Enabling it would require a separate provider, strict header redaction, bounded caching, explicit failure semantics, and evidence that observation does not consume quota. No browser cookie extraction is implemented.

## Local trust boundary

Anyone who can read the Windows user profile can potentially read the SQLite history. The database is not encrypted at rest. Use normal Windows account protection and disk encryption when usage history is sensitive.

The monitor does not claim that undocumented server behavior will never change. If a method's read-only semantics become uncertain, the safe behavior is to disable it and show unsupported/unavailable.
