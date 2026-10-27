# Kapaat

> **Kapaat** (Punjabi: ਕਪਾਟ — *cabinet, storage compartment*) is a self-hosted storage inventory app that tracks what's inside every physical storage box, where each box lives, and surfaces it through a fast single-page web UI.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688)](https://fastapi.tiangolo.com/)

---

## Core Features

| Feature | Description |
|---|---|
| **Location hierarchy** | Room → Zone → Shelf → Bin — multi-select filter chips for each level |
| **Items table** | Photo thumbnail, name, category, qty, location, and tags in one view |
| **Inline editing** | Edit any item's name, category, quantity, and tags without leaving the page |
| **Move items** | Move one or many items to a different bin via a modal picker |
| **Bulk operations** | Select across bins — bulk add/remove tags, bulk move |
| **Tags** | Preset seasonal tags + custom tags; per-tag color coding; tag filter |
| **Photos** | Per-item and per-bin photo upload (up to 20 MB); tap thumbnail to zoom |
| **QR labels** | Auto-generated QR per bin — scan on mobile to see contents; print multi-label sheets (QR left, bin name right) in standard label sizes |
| **Search** | Full-text across name, category, box ID, and tags |
| **Export** | Download full inventory as CSV or XLSX (formula-injection safe) |
| **Backup / restore** | One-click backup (DB + photos as `.zip`); retention pruning; restore via CSV import |
| **Authentication** | Local username/password login; optional OIDC via Authentik; optional email/TOTP MFA |
| **Access control** | Session-based auth with `admin` / `write` / `read` scopes; optional machine `SERVICE_API_KEY` for automation |
| **Sheets sync** | Optional n8n webhook integration for Google Sheets bidirectional sync |

---

## Quick Start (local)

**Requirements:** Python 3.11+, pip

```bash
git clone https://github.com/nomi25home/kapaat.git
cd kapaat

python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Generate the required secret and set BASE_URL at minimum
echo "AUTH_SECRET_KEY=$(openssl rand -base64 32)" >> .env
# Edit .env and update BASE_URL if your server is not localhost

set -a && source .env && set +a
uvicorn app:app --reload --port 8096
```

Open [http://localhost:8096](http://localhost:8096). The SQLite database and photo store are created automatically on first run at the paths defined in `.env`.

---

## Docker (production)

### Minimal `docker-compose.yml`

```yaml
services:
  kapaat:
    image: ghcr.io/nomi25home/kapaat:1   # or build: .
    restart: unless-stopped
    ports:
      - "8096:8096"
    volumes:
      - kapaat_data:/data
    environment:
      - BASE_URL=https://storage.yourdomain.com
      - AUTH_SECRET_KEY=                              # required: openssl rand -base64 32
      - N8N_WEBHOOK_URL=                              # leave blank to disable
      - TZ=America/New_York

volumes:
  kapaat_data:
```

### Building from source

```bash
docker build -t kapaat .
docker run -d -p 8096:8096 \
  -v kapaat_data:/data \
  -e BASE_URL=http://192.168.1.10:8096 \
  -e AUTH_SECRET_KEY=$(openssl rand -base64 32) \
  kapaat
```

---

## Configuration

All configuration is via environment variables. Copy `.env.example` to `.env` and fill in your values.

### Core

| Variable | Default | Description |
|---|---|---|
| `BASE_URL` | `http://localhost:8096` | Public URL used to build QR code deep-links. Must be reachable from phones on your network. |
| `DB_PATH` | `/data/garage_inventory.db` | SQLite database path inside the container. |
| `PHOTOS_DIR` | `/data/photos` | Photo storage directory inside the container. |
| `MAX_PHOTO_BYTES` | `20971520` (20 MB) | Maximum photo upload size in bytes. |
| `APP_TITLE` | `Kapaat` | Browser tab title and API docs title. |
| `LOCALE` | `en` | UI language code — must match a file in `locales/`. |
| `TZ` | `America/New_York` | Timezone for timestamps. |
| `DB_ENCRYPTION_KEY` | *(empty — disabled)* | Optional passphrase for AES-256 on-disk encryption via SQLCipher. Requires `ENABLE_SQLCIPHER=1` build arg. **If you lose this key, your data is unrecoverable.** If `pysqlcipher3` is unavailable the app will refuse to start rather than silently fall back to plaintext. |

### Authentication

| Variable | Default | Description |
|---|---|---|
| `AUTH_SECRET_KEY` | *(required)* | Secret key for signing session cookies. Generate with `openssl rand -base64 32`. The app refuses to start if this is missing or left at the example placeholder. |
| `SERVICE_API_KEY` | *(empty — disabled)* | Static bearer token for machine-to-machine access (n8n, scripts). When unset, `require_read` routes are open (backward-compatible); a startup WARNING is logged. |
| `SERVICE_API_SCOPES` | `read,write` | Comma-separated scopes granted to `SERVICE_API_KEY` — `read`, `write`, and/or `admin`. |

### OIDC (Authentik)

Leave all three blank to disable OIDC and use local login only.

| Variable | Default | Description |
|---|---|---|
| `AUTHENTIK_CLIENT_ID` | *(empty)* | OAuth2 client ID from your Authentik application. |
| `AUTHENTIK_CLIENT_SECRET` | *(empty)* | OAuth2 client secret. |
| `AUTHENTIK_ISSUER_URL` | *(empty)* | Your Authentik provider URL, e.g. `https://auth.yourdomain.com/application/o/kapaat`. |
| `ALLOWED_EMAILS` | *(empty — allow all)* | Comma-separated list of email addresses permitted to log in via OIDC. |
| `BLOCKED_EMAILS` | *(empty)* | Comma-separated list of email addresses always denied. |
| `ADMIN_GROUP` | `admins` | Authentik group name whose members get admin scope. |

### MFA (email OTP)

| Variable | Default | Description |
|---|---|---|
| `MFA_EMAIL_BACKEND` | `log` | `log` (prints OTP to stdout — dev only), `sendgrid`, or `smtp`. |
| `MFA_FROM_EMAIL` | `kapaat@example.com` | Sender address for OTP emails. |
| `MFA_SENDGRID_API_KEY` | *(empty)* | SendGrid API key (when `MFA_EMAIL_BACKEND=sendgrid`). |
| `MFA_SMTP_HOST` | `localhost` | SMTP host (when `MFA_EMAIL_BACKEND=smtp`). |
| `MFA_SMTP_PORT` | `587` | SMTP port. |
| `MFA_SMTP_USER` | *(empty)* | SMTP username. |
| `MFA_SMTP_PASSWORD` | *(empty)* | SMTP password. |

### Integrations

| Variable | Default | Description |
|---|---|---|
| `N8N_WEBHOOK_URL` | *(empty — disabled)* | n8n webhook for Google Sheets sync. Leave blank to disable. |
| `N8N_WEBHOOK_SECRET` | *(empty)* | Optional secret validated on incoming `sync-row` requests. |
| `N8N_CA_BUNDLE` | *(empty)* | Path to a CA bundle for private TLS certs on your n8n host. |

> **Tip — QR scanning away from home:** `BASE_URL` must match what your phone can reach. On a local network, use your server's LAN IP (e.g. `http://192.168.1.10:8096`). For off-site scanning, set `BASE_URL` to your [Tailscale](https://tailscale.com/) IP or a zero-trust tunnel hostname — the QR deep-links will resolve wherever the phone has a Tailscale connection, making garage scans work even from a friend's WiFi.

---

## Data Portability & Migration FAQ

**Where is my data stored?**  
Everything lives in a single SQLite file (`garage_inventory.db`) and a flat photo directory (`photos/`). Both are inside the Docker volume mapped to `/data`.

**How do I back up my data?**  
The easiest way is the **Download full backup** button in the navbar (the `backup` icon). It streams a `.zip` containing a live DB snapshot and all photos directly to your browser — no shell required.

For automated or scheduled backups, use the shell approach:
```bash
docker run --rm -v kapaat_data:/data -v $(pwd):/backup alpine \
  tar czf /backup/kapaat-backup-$(date +%F).tar.gz /data
```

Or hit the API directly (admin auth required — use your browser session cookie or a `SERVICE_API_KEY` with admin scope):
```bash
curl -H "Authorization: Bearer YOUR_SERVICE_API_KEY" \
     -o kapaat-backup.zip https://bins.yourdomain.com/api/backup/download
```

**How do I restore from a backup?**

*From the UI `.zip` backup* (DB + photos):
```bash
# Extract the zip into a new Docker volume
docker volume create kapaat_data_restored
docker run --rm \
  -v kapaat_data_restored:/data \
  -v $(pwd):/backup \
  alpine sh -c "apk add --no-cache unzip && unzip /backup/kapaat_backup_*.zip -d /data"

# Start the app pointing at the restored volume
docker run -d -p 8096:8096 \
  -v kapaat_data_restored:/data \
  -e BASE_URL=http://localhost:8096 \
  -e AUTH_SECRET_KEY=$(openssl rand -base64 32) \
  ghcr.io/nomi25home/kapaat:1
```

*From a shell `tar.gz` backup:*
```bash
docker volume create kapaat_data_restored
docker run --rm \
  -v kapaat_data_restored:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/kapaat-backup-YYYY-MM-DD.tar.gz -C /
```

> **Note:** CSV import (`POST /api/import-csv`) restores item rows only — photos and bin structure are not included.

**How do I move to a new host?**  
Follow the restore steps above on the new host using a fresh backup from the old one. No schema migrations are needed — the app runs `ALTER TABLE` migrations on startup automatically.

**Can I use a different database?**  
Not currently — SQLite is intentional to keep the deployment footprint to a single file. Contributions adding a Postgres adapter are welcome.

**How do I reset everything?**  
Delete (or rename) the Docker volume: `docker volume rm kapaat_data`.

---

## Architecture

```
browser  ──HTTP──▶  FastAPI (app.py)
                        │
                   Jinja2 template (templates/index.html)
                   Single-page, vanilla JS, no build step
                        │
              ┌─────────┴──────────┐
         SQLite DB            /data/photos/
       (garage_inventory.db)   (flat file store)
                        │
                  optional n8n webhook
                  (Google Sheets sync)
```

- **Backend:** FastAPI + uvicorn; pure Python stdlib + SQLite for zero-dependency data layer.
- **Frontend:** Single Jinja2 template rendered server-side on first load; all subsequent interactions are fetch-based JSON API calls. No JavaScript framework, no build step.
- **Storage:** SQLite for structured data, flat files for photos. Both live in one Docker volume for trivial backup and portability.

---

## API Reference

Auth column: **admin** = admin session or `SERVICE_API_KEY` with `admin` scope; **write** = admin or write scope; **read** = any authenticated session (or open when `SERVICE_API_KEY` unset); **public** = no auth required.

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/` | read | Main dashboard |
| `GET` | `/login` | public | Login page (local or OIDC) |
| `GET` | `/auth/callback` | public | OIDC callback — redirects to `/` on success |
| `POST` | `/login-mfa` | public | Initiate MFA OTP (returns challenge) |
| `POST` | `/login-mfa/verify` | public | Verify OTP and create session |
| `GET` | `/logout` | public | Clear session and redirect to login |
| `GET` | `/bin/{bin_id}` | public | Redirects to `/scan/{bin_id}` (QR deep-link compat) |
| `GET` | `/scan/{bin_id}` | public | Mobile QR scan view — shows bin contents |
| `GET` | `/api/bins` | read | All bins (JSON) |
| `GET` | `/api/items?search=` | read | All items, optional full-text search |
| `GET` | `/api/tag-colors` | read | Custom tag color mappings |
| `GET` | `/photos/{filename}` | read | Serve a stored photo |
| `POST` | `/api/sync-row` | public* | Ingest a row from Google Sheets (n8n); validated by `N8N_WEBHOOK_SECRET` if set |
| `GET` | `/api/sync-conflicts` | read | List unresolved sync conflicts |
| `POST` | `/api/sync-conflicts/{id}/resolve` | admin | Resolve a sync conflict |
| `POST` | `/add-bin` | admin | Register a new bin |
| `PATCH` | `/update-bin/{bin_id}` | admin | Edit bin zone / room / shelf / container |
| `DELETE` | `/delete-bin/{bin_id}` | admin | Delete an empty bin |
| `POST` | `/add-item` | write | Add item to a bin |
| `PATCH` | `/update-item/{item_id}` | admin | Edit item fields |
| `DELETE` | `/delete-item/{item_id}` | admin | Delete item |
| `POST` | `/api/move-items` | admin | Move items to a different bin |
| `POST` | `/api/bulk-tag` | admin | Add or remove tags across many items |
| `POST` | `/api/tag-colors` | write | Set a tag's hex color |
| `POST` | `/upload-photo/{type}/{id}` | admin | Upload photo (`type`: `item` or `bin`) |
| `GET` | `/export/{csv\|xlsx}` | admin | Download full inventory |
| `POST` | `/api/import-csv` | admin | Import inventory from CSV |
| `GET` | `/api/backup` | admin | Download a point-in-time SQLite snapshot (`.db`) |
| `GET` | `/api/backup/download` | admin | Download a full backup archive (DB + photos as `.zip`) |
| `GET` | `/api/backup/retention` | admin | List backups eligible for pruning |
| `POST` | `/api/backup/retention` | admin | Prune old backups per retention policy |

### Google Sheets sync — conflict strategy

`/api/sync-row` is a **Sheet → App** write path only. It creates a new item when the row has no `Item ID`; it does not update existing items.

**What happens on a simultaneous edit?**

| Scenario | Outcome |
|---|---|
| Item edited in Kapaat while the same row is unchanged in Sheets | Safe — Sheets later syncs the original values on next n8n run; they do not overwrite the Kapaat edit because `sync-row` only inserts rows with no `Item ID`. |
| Item name changed in both Kapaat and Sheets before next n8n run | Kapaat wins — the Sheets row already has an `Item ID`, so `sync-row` skips it. The mismatch is visible in Sheets. |
| Item deleted in Kapaat; row still in Sheets | The row's `Item ID` is orphaned in Sheets. A subsequent n8n run sees the `Item ID` present and skips re-insertion. Clean up the Sheets row manually or via a cleanup workflow. |

The sync is intentionally append-only to prevent silent overwrites of locally edited data.

---

## Database Schema

```sql
bins           (bin_id PK, zone, shelf_number, color_code, room, bin_photo, last_synced_at)
items          (item_id PK, bin_id FK, name, category, quantity, tags, item_photo, version, last_synced_at)
tag_colors     (tag_name PK, hex)
audit_log      (id PK, actor, action, item_id, details, timestamp)
sync_conflicts (id PK, item_id, bin_id, name, category, quantity, source, resolved, created_at)
_schema_version(version PK, applied_at)
```

Columns added in later schema versions (`room`, `tags`, `item_photo`, `bin_photo`, `version`, `last_synced_at`) are applied via idempotent `ALTER TABLE` migrations at startup. Existing databases upgrade automatically with no manual steps.

---

## Contributing

See [CONTRIBUTING.md](.github/CONTRIBUTING.md). Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before participating.

Before cutting a release, run through the manual test plan in [`docs/release-test-plan.html`](docs/release-test-plan.html) — open it in any browser, no server required. When creating a release tag, use the `v` prefix (e.g. `v1.3.6`) so CI triggers the Docker image build automatically.

## Security

See [SECURITY.md](.github/SECURITY.md) for the responsible disclosure policy.

## License

[MIT](LICENSE) © 2025 nomi25home
