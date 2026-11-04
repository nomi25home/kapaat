# Kapaat Roadmap

## Now: v2.0.0 (released 4 November 2026)

Kapaat 2 is a rewrite with a deliberately small scope. See the [release notes](docs/release-notes/v2.0.0.md).

- Postgres + FastAPI API + React PWA, as three containers
- Rooms › zones › bins › items; items can be added before they have a bin
- Onboard and offboard (retire/restore) for items and bins; bulk move
- Check-out / check-in with history
- Exact-size label PDFs: 48 mm tape (default), Brother DK 62 mm, Avery L7160 / 5160, plain A4/Letter with crop marks
- Installable phone app with camera scanning and read-only offline mode
- Email-code sign-in, invites, API tokens; optional passkeys and OIDC
- Signed webhook outbox and a Google Sheets Apps Script
- One-time importer from v1

## Before calling v2 "done"

Real-hardware checks that automated tests can't cover (tracked in the [test plan](docs/release-test-plan.html)):

- Print the 48 mm label on a label maker and the A4/Letter sheets on an inkjet at 100%, and scan them through clear tape
- Camera scanning on an iPhone and an Android phone over HTTPS
- Real SMTP delivery, a real OIDC provider, a real Google Sheet
- Import a copy of the household v1 database

## Ideas (not committed)

Each of these should earn its place against the goal of keeping Kapaat small.

- **Scheduled backups** — an optional `pg_dump` sidecar with retention, so backups don't depend on remembering a command.
- **Translations** — v1 shipped an `en.json` locale file that v2 dropped; bring back i18n if there's demand.
- **Low-stock hints** — a minimum quantity per item and a "running low" filter.
- **Item labels in bulk** — print labels for many items at once from the item list (single item labels already exist).
- **Public demo instance** — read-only, reset nightly, for the awesome-selfhosted listing.
- **Structured logs and a health dashboard** — JSON logs and a simple metrics endpoint for people who run monitoring.

Not planned: two-way spreadsheet sync (it caused conflicts in v1), multi-tenant hosting, and an offline write queue.

## History: v1 (October 2026)

v1 was a single FastAPI file on SQLite with Jinja templates. Milestones, in order:

| Version | Highlights |
|---|---|
| 1.1 | Browser-driven `.zip` backups; optional SQLCipher encryption |
| 1.2.1 | Schema migration registry, audit log, optimistic locking, backup retention, sync-conflict banner |
| 1.2.2 | Email allow/block lists, admin group, email OTP login, design system |
| 1.2.3 – 1.2.4 | Security hardening (OTP backoff, CSRF, startup secret checks); test stacks; sample n8n workflow |
| 1.3.0 | Security audit remediation (25 findings), horizontal QR labels, pytest in CI, manual test plan |
| 1.3.1 – 1.3.7 | Fixes: Starlette 1.7 templates, setup docs, CI tag handling, responsive header, label gaps and 48 mm default |

The v1 design documents are kept in [docs/history](docs/history/), and v1 images remain at `ghcr.io/nomi25home/kapaat:1`.
