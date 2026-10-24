# Kapaat Roadmap

This document outlines the core post-v1.0.0 developmental milestones for Kapaat, prioritizing operational flexibility, multi-user concurrency, and data durability.

## Shipped in v1.1.0

### ✅ 1. Unified Browser-Driven Backups
*   **Delivered:** `/api/backup/download` endpoint + navbar button.
*   Hot-copies the live SQLite database via `sqlite3.backup()`, bundles all `photos/` assets, and streams a compressed `.zip` to the browser. One click from the navbar.

### ✅ 2. Transparent Database Storage Encryption
*   **Delivered:** Optional SQLCipher support via `DB_ENCRYPTION_KEY` env var.
*   When set, the app swaps in `pysqlcipher3` at runtime for AES-256 on-disk encryption. Requires `ENABLE_SQLCIPHER=1` Docker build arg. Falls back to plain SQLite with a printed warning if the library is absent.

## Shipped in v1.2.x (Active Phase: Multi-User & Hardening)

### ✅ 3. Schema Migrations & Version Control
*   **Delivered:** Migration registry in `_schema_version` table (v1.2.1).
*   Abstracted table setups into versioned migration functions; eliminated raw `ALTER TABLE` startup commands. Migrations are idempotent and run once.

### ✅ 4. Deterministic Webhook Sync & Conflict Detection
*   **Delivered:** `/api/sync-row` with `N8N_WEBHOOK_SECRET` auth, optimistic locking, and `sync_conflicts` table (v1.2.2).
*   Idempotent upserts by `item_id`, conflict detection populates dashboard banner, append-only protection against silent Sheets stomps.

### ✅ 5. Multi-User Access Control (Email Gate + Admin)
*   **Delivered:** `ALLOWED_EMAILS` / `BLOCKED_EMAILS` whitelist/blacklist at OIDC callback, per-IP exponential backoff on auth failures, `ADMIN_GROUP` membership check (revocable at next login), `require_admin()` on all mutating routes (v1.2.2).

### ✅ 6. Email + OTP Login Flow (Authentik-Alternative)
*   **Delivered:** `/login` → `/login-mfa` → `/login-mfa/verify` with 6-digit OTP, 5-min expiry, in-memory store, whitelist-only delivery, multiple backends (`smtp`, `sendgrid`, `log`, `none`) (v1.2.2).

### ✅ 7. Design System Formalization
*   **Delivered:** `DESIGN.md` + `tokens.json` with color, typography, spacing, component specs, motion, accessibility, anti-slop rules; login/MFA screens match dashboard tokens (v1.2.2).

### ✅ 8. CSO Security Hardening
*   **Delivered (v1.2.3):**
    - Fix 4: OTP brute-force protection — per-email exponential backoff on `/login-mfa/verify` (0→2→5→15→60s), delays applied before response to prevent timing side-channels.
    - Fix 6: CSRF protection on all state-changing routes — `CSRFMiddleware` validates `X-CSRF-Token` header against per-session token; exempt paths: `/login-mfa`, `/login-mfa/verify`, `/logout`, `/api/sync-row`.
    - Fix 7: Fail startup if `AUTH_SECRET_KEY` is default/empty — `RuntimeError` at module load for known bad values.

### ✅ 9. Test Stacks for Independent Validation
*   **Delivered (v1.2.4):** Three isolated container instances on 192.168.74.45:
    - `garage-storage` (8099) — Production, Authentik OIDC
    - `garage-storage-test-auth` (8102) — Test, Authentik OIDC
    - `garage-storage-test-mail` (8103) — Test, Email+MFA whitelist
*   Each with isolated `.env` (`DB_PATH`, `PHOTOS_DIR`, `APP_TITLE`), enabling per-instance code change validation without affecting production.

### ✅ 10. Sample n8n Workflow
*   **Delivered (v1.2.4):** `n8n/kapaat-sync-workflow.json` — reference workflow mapping kapaat webhook payload to Google Sheets append action; no secrets embedded.

---

## Next Phase: Operational Maturity & External Sync (P3)

### 11. Google Sheets Sync — Production-Grade
*   **Goal:** Turn the sample n8n workflow into a documented, supported sync pattern with retry, dedup, and conflict resolution.
*   **Scope:** 
    - Define official webhook payload schema (already stable).
    - Document n8n workflow import steps, required credentials, sheet layout.
    - Add idempotency keys to prevent duplicate rows on webhook retries.
    - Add "last synced" timestamp per bin/item for incremental sync visibility.
    - Support bidirectional sync (Sheets → kapaat) for bulk edits.

### 12. Litestream Replication (Disaster Recovery)
*   **Goal:** Continuous SQLite replication to S3/GCS/bucket for zero-config HA.
*   **Scope:** Add `litestream` sidecar to container stack; replicate `garage_inventory.db` to configurable bucket on every write; document restore procedure.

### 13. Observability: Structured Logging + Metrics
*   **Goal:** Emit JSON logs + Prometheus metrics for request latency, error rates, sync failures.
*   **Scope:** Add `structlog` + `prometheus-fastapi-instrumentator`; expose `/metrics`; log audit events, sync outcomes, auth failures with correlation IDs.

### 14. API Token / Service Account Auth
*   **Goal:** Allow programmatic access for n8n, scripts, CI without user session.
*   **Scope:** New `SERVICE_API_KEY` env var; token-based auth for `/api/*` routes; scoped permissions (read-only vs write).

### 15. Mobile-Optimized Single-Bin Scan View
*   **Goal:** Read-only, one-handed phone view for garage scanning (per DESIGN.md §5.2).
*   **Scope:** New route `/scan/{bin_id}` with centered card, large QR, minimal chrome, no drawer/table chrome.

### 16. Bulk Import / Export UI
*   **Goal:** CSV/Excel import-export from the browser with preview & conflict resolution.
*   **Scope:** New drawer/modal for CSV upload; column mapping UI; dry-run preview; transactional commit with audit log.

---

## Research / Future

### 17. PostgreSQL Migration Path (Optional)
*   If scale demands it: add `postgres` service to stack, provide `DB_DRIVER=postgresql` env switch, run migrations against both dialects in CI.

### 18. Real-Time Multi-User Presence
*   WebSocket or SSE for live cursor/row presence when multiple admins edit same bin.

### 19. Plugin / Hook System
*   Allow users to inject custom validation, webhook transforms, or export formats without forking.