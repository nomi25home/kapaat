# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 2.x (latest release and `main`) | ✅ |
| 1.x | ❌ — please upgrade ([migration guide](../docs/migration-from-v1.md)) |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

To report a security issue responsibly:

1. Email **nomi25home@gmail.com** with the subject line `[SECURITY] Kapaat — <brief description>`.
2. Include:
   - A clear description of the vulnerability and its potential impact.
   - Steps to reproduce (proof-of-concept if possible).
   - Any suggested remediation.
3. You will receive an acknowledgement within **72 hours**.
4. If confirmed, a fix will be prioritised and a patched release issued within a reasonable timeframe (target: 14 days for critical issues).
5. You will be credited in the release notes unless you prefer to remain anonymous.

## Scope

This project is a self-hosted homelab application. Typical concerns include:

- API endpoints reachable without signing in, or member accounts reaching admin-only actions.
- Weaknesses in email-code sign-in (guessing, replay, account enumeration), sessions, CSRF protection, passkeys or OIDC.
- API tokens that can do more than their scope (read-only tokens writing).
- Path traversal or arbitrary file read/write via photo upload or download.
- SQL injection in search or filter parameters.
- Stored XSS in item, bin, tag or location names.
- Formula injection in CSV exports or the Google Sheets webhook payload.
- Webhook signing flaws (forged or replayable deliveries).

## Out of Scope

- Vulnerabilities that require physical access to the host machine.
- Issues in upstream dependencies (report directly to those maintainers; open a Dependabot PR here as well).
- Denial-of-service against a self-hosted instance (rate limits exist for sign-in only).
- Server-side requests made by the webhook: its URL is set by an admin, who is trusted.
- Deployments exposed over plain HTTP; run Kapaat behind HTTPS with `COOKIE_SECURE=true`.
