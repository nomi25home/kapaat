# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.3.3] — 2026-10-27

### Fixed

- `docker-compose.yml` now passes `AUTH_SECRET_KEY` and `BASE_URL` via env-var substitution so the app starts correctly out of the box.
- README "Building from source" `docker run` example now includes `-e AUTH_SECRET_KEY=$(openssl rand -base64 32)`.
- `pyproject.toml` version synchronized to `1.3.3`.

---

## [1.3.2] — 2026-10-27

### Fixed

- README quick-start generates `AUTH_SECRET_KEY` automatically and documents it as required for Docker Compose.
- Single-bin QR view now uses the server-computed `qr_url` instead of a hardcoded developer IP.
- Removed global `# ruff: noqa` from `app.py`; all Ruff findings addressed.
- CI smoke-test step added before pytest; `PHOTOS_DIR` set to `/tmp/smoke-photos` to avoid `/data` permission error on CI runners.
- Restore documentation includes concrete shell commands for both `.zip` (UI backup) and `.tar.gz` (shell backup) formats; Alpine restore example adds `apk add --no-cache unzip`.

---

## [1.3.1] — 2026-10-27

### Fixed

- All HTML routes (`/`, `/login`, `/scan/{bin_id}`, and OTP error paths) returned HTTP 500 due to a breaking API change in Starlette 1.7.0: `TemplateResponse` now requires `request` as its first positional argument rather than a key inside the context dict. Updated all 8 call sites in `app.py`. (#15)

---

## [1.3.0] — 2026-10-27

This release completes a full security audit remediation (25 findings across 4 PRs), adds horizontal QR label printing, and ships a manual release test plan.

### Security

- **CRITICAL** — Added `require_admin` to `GET /api/backup`, `GET /api/backup/download`, `GET /export/{file_type}`, and `POST /add-item`; these routes were previously unauthenticated
- **CRITICAL** — `GET /api/backup/retention` converted from a destructive unauthenticated GET (called `unlink()`) to a safe read-only listing; deletion moved to the existing `POST /api/backup/retention` (admin-only)
- **CRITICAL** — Fixed OIDC `auth_callback` missing `return` statement — successful Authentik logins were returning HTTP 200 null body instead of redirecting to the dashboard
- **HIGH** — SQLCipher import failure now raises `RuntimeError` instead of silently clearing `DB_ENCRYPTION_KEY` and continuing with unencrypted SQLite
- **HIGH** — OTP generation replaced `random.randint` with `secrets.randbelow(1_000_000)` (cryptographically secure)
- **HIGH** — OIDC rate limiter now expires attempt records after a 15-minute window; counters no longer accumulate forever
- **HIGH** — `time.sleep()` in async handlers replaced with `await asyncio.sleep()` (was blocking the event loop)
- **HIGH** — CSRF middleware blanket `/api/` exemption replaced with a precise Bearer/`X-API-Key` header check (PR #5)
- **HIGH** — n8n webhook `verify=False` removed; added `N8N_CA_BUNDLE` env var for private CA support
- **MEDIUM** — Added `require_read` to `GET /api/sync-conflicts`, `GET /api/tag-colors`, and `GET /photos/{filename}`
- **MEDIUM** — Startup now logs a WARNING when `SERVICE_API_KEY` is unset, making open-mode explicit in container logs
- **LOW** — CSV and XLSX export now prefix formula-injection characters (`=`, `+`, `-`, `@`, tab, CR) with `'` via `_sanitize_cell()`
- **LOW** — DB migration `OperationalError` handling narrowed to only swallow `"duplicate column name"`; all other errors re-raise

### Added

- `GET /bin/{bin_id}` redirect route → `GET /scan/{bin_id}` for QR deep-link backward compatibility (printed labels using `/bin/` now resolve correctly)
- `N8N_CA_BUNDLE` env var for custom CA bundles when n8n uses a private TLS certificate
- Startup WARNING log when `SERVICE_API_KEY` is unset (open-mode notice)
- `docs/release-test-plan.html` — standalone interactive manual test checklist (40 test cases, 8 areas; open in any browser, no server required)
- pytest job added to CI — runs the full test suite before the Docker build step

### Changed

- QR label print layout changed from vertical (QR top, name below) to horizontal (QR left, name right); landscape labels use full height for QR; square labels use 62% width for QR
- Default label size preset changed to `2.75" × 1.5"` (tiles 3 × 7 = 21 labels per A4 sheet)
- `.gitignore` expanded to a standard Python project ignore file (covers `.env`, `*.db`, `__pycache__/`, `.venv/`, `/data/`, etc.)
- `.env.example` `AUTH_SECRET_KEY` changed from a shipped default value to a blank field with `openssl rand -base64 32` generation instruction
- GitHub Actions pinned to Node.js 24 compatible versions (`actions/checkout@v4.2.2`, `actions/setup-python@v5.3.0`)
- README expanded with authentication docs, full env var reference, auth-annotated API table, current DB schema, and link to test plan
- Removed duplicate `docker-publish.yml` workflow; `release.yml` retained

### Fixed

- Version inconsistency between `VERSION` file and `app.py` default resolved (unified to `1.3.0`)

---

## [1.2.2] — 2026-10-23

### Fixed
- Email gate at login: `ALLOWED_EMAILS` whitelist, `BLOCKED_EMAILS` blacklist; blocklist wins if both set; all users (including admins) must pass; non-matching → 403
- Backoff algorithm on repeated auth failures from one IP: 0s → 5s → 15s → 30s → 60s capped
- Admin = Authentik group (`ADMIN_GROUP`), checked at login and on every mutating request; email gate runs first
- `sync-row` now requires `N8N_WEBHOOK_SECRET` query parameter; acts as `SERVICE_USER_SUB`; bypasses email gate
- Added deterministic update path for `/api/sync-row` (mode=update); sheet→app sync now supports modifies, not just inserts
- Conflict detection now populates `sync_conflicts` table when sheet and app disagree; `/api/sync-conflicts` banner now shows real mismatches

### Changed
- Non-admins are view-only; admins may edit. Email gate applies to everyone.
- `sync_conflicts` table is no longer dead — it is populated on actual conflicts.

### Added
- `ALLOWED_EMAILS`, `BLOCKED_EMAILS` env vars (documented in `.env.example`)
- `ADMIN_GROUP` env var (default `admins`)
- `N8N_WEBHOOK_SECRET`, `SERVICE_USER_SUB` env vars
- Backoff delay on auth failures
- `sync_conflicts` population on `/api/sync-row` conflict
- `test_non_admin_denied_on_mutating_route` test

### Security
- Authentik group membership is revocable — change membership in Authentik, next login takes effect
- All auth failures sleep before responding, denying timing side-channels
- Whitelist is active only when non-empty; empty = whitelist off
- Blacklist wins over whitelist when both are configured

---

## [1.2.1] — 2026-10-22

### Fixed
- `/api/sync-row` now honors an incoming `item_id`: if the item already exists it is skipped instead of inserting a duplicate row (`sync-row-skip-existing` audit entry).
- Dashboard banner now shows unresolved sync conflicts from `/api/sync-conflicts`, with per-conflict "Mark resolved" buttons.
- Backup retention is now enforced on every backup download, not only on manual `/api/backup/retention` trigger.
- Audit rows are no longer silently dropped: `log_audit()` commits its own row, and `bulk_tag` audit calls survive rollback.
- `PATCH /update-item/{id}` now rejects a missing or invalid `version` field (400) instead of silently succeeding — the optimistic lock is no longer vacuous.

### Added
- `audit_log` and `sync_conflicts` tables (migration v3).
- `version` column on `items` for optimistic locking (migration v2).
- Migration registry (`_migrate_v1`/`v2`/`v3`) — no raw `ALTER TABLE` outside the registry.
- `/api/backup/retention` and `/api/sync-conflicts` endpoints.

## [0.1.0] — 2025-10-20

### Added
- Multi-level location hierarchy: Zone → Room → Shelf → Bin
- Multi-select filter chips for Zone, Room, and Box
- Items table with photo thumbnails, name, category, qty, location, and tags
- Inline item editing (name, category, quantity, tags)
- Move items between bins — single item and bulk
- Bulk tag add / remove across multiple selected items
- Per-tag color coding with a swatch palette picker
- Tag filter (multi-select) in the filter bar
- Per-item and per-bin photo upload and full-screen zoom
- QR code labels per bin — print and mobile scan view
- Full-text search across name, category, box ID, and tags
- CSV and XLSX inventory export
- Google Sheets sync via optional n8n webhook (inbound + outbound)
- Edit bin metadata (zone, room, shelf, container description)
- `PATCH /update-bin` and `POST /api/move-items` API endpoints
- Environment-variable configuration (`BASE_URL`, `N8N_WEBHOOK_URL`, `DB_PATH`, `PHOTOS_DIR`, `APP_TITLE`)
- MIT License, `.env.example`, `.dockerignore`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`

[Unreleased]: https://github.com/nomi25home/kapaat/compare/v1.3.1...HEAD
[1.3.1]: https://github.com/nomi25home/kapaat/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/nomi25home/kapaat/compare/v1.2.5...v1.3.0
[1.2.2]: https://github.com/nomi25home/kapaat/compare/v1.2.1...v1.2.2
[1.2.1]: https://github.com/nomi25home/kapaat/compare/v1.2.0...v1.2.1
[0.1.0]: https://github.com/nomi25home/kapaat/releases/tag/v0.1.0
