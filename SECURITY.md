# Security policy

## Reporting a vulnerability

Please use the repository's **Security → Report a vulnerability** flow so the report is handled through a private GitHub Security Advisory. Do not open a public issue containing credentials, account data, cookies, raw quota responses, or local database contents.

Include the affected version, a minimal reproduction, impact, and whether the behavior can cross the read-only RPC boundary. Replace all identifiers and usage values with synthetic examples.

## Security scope

High-priority reports include:

- any path that can send a non-allowlisted App Server request;
- credential, cookie, identifier, or private response leakage;
- unsafe command execution or path handling;
- remote data upload that occurs without explicit user action;
- local database disclosure or corruption;
- packaged dependency substitution.

Incorrect estimates without a security boundary failure are ordinary bugs, but they should still be reported because the UI must not present fabricated precision.
