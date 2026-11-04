# Moving from Kapaat v1 to v2

Kapaat 2 is a rewrite with a smaller, clearer scope. It runs as three containers (Postgres, API, web app) instead of one, and keeps its data in Postgres instead of SQLite. Your v1 data comes across with a one-time import.

## What changes

| v1 | v2 |
|---|---|
| One container, SQLite (optionally SQLCipher), Litestream | `db` (Postgres) + `api` + `web`, backups with `pg_dump` |
| Bin "zone" and "room" fields | **Room › Zone › Bin** hierarchy you manage under *Places* |
| Login: Authentik OIDC + email OTP, `ALLOWED_EMAILS` | Email code by default; OIDC and passkeys optional. People are invited from *More → People* |
| `SERVICE_API_KEY` | Per-person API tokens (read or read/write) |
| n8n workflow + sync conflicts | One signed webhook; Google Sheets via a copy-paste Apps Script ([guide](sheets-webhook.md)). One-way, so no conflicts |
| Labels rendered by the browser | Exact-size PDFs: 48 mm tape (default), Brother DK 62 mm, Avery L7160 / 5160, plain A4/Letter with crop marks |
| — | Check-in/check-out, retire/restore for items and bins, items without a bin, installable PWA with camera scanning |

Old printed QR labels keep working: v2 understands the v1 `/bin/<id>` and `/scan/<id>` links, and imported bins keep their v1 IDs as their codes.

## Steps

1. **Back up v1.** In v1, use *Download full backup (.zip)*, or copy the Docker volume. Keep v1 stopped but don't delete it until you're happy with v2.

2. **Unpack the v1 data somewhere readable**, e.g. `/srv/kapaat-v1/` containing `storage.db` (your database file; its name may differ) and `photos/`. If v1 used SQLCipher encryption, decrypt a copy first; the importer reads plain SQLite.

3. **Start v2** following the README, sign in once so your admin account exists.

4. **Dry run** — reads v1 read-only and shows what would happen, writing nothing:

   ```bash
   docker compose run --rm -v /srv/kapaat-v1:/v1:ro api \
     python -m scripts.import_v1 --sqlite /v1/storage.db --photos /v1/photos --dry-run
   ```

   Read the warnings. Typical ones: a bin ID with spaces or symbols gets a cleaned-up code (reprint that label), a photo file is missing, an item pointed at a bin that no longer exists (it's imported without a bin).

5. **Import for real** — same command without `--dry-run`. Running it again later is safe: anything already imported is skipped.

## How v1 fields map

| v1 | v2 |
|---|---|
| `bins.zone` (e.g. "Garage") | Room |
| `bins.room` (e.g. "North wall"); blank becomes "General" | Zone inside that room |
| `bins.shelf_number` | Bin notes ("Shelf 2") |
| `bins.bin_id` | Bin code |
| `bins.color_code` | Bin colour (invalid values fall back to Kapaat cyan) |
| `items.*`, comma-separated `tags`, `tag_colors` | Items, tags and tag colours |
| Item and bin photos | Re-encoded JPEGs (EXIF and location data stripped) |
| `audit_log` | Item history entries marked "Kapaat v1" |

Not imported: sync-conflict records, n8n settings, and users. Invite people from *More → People*; they sign in with the same email address.
