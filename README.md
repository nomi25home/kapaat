<p align="center">
  <img src="brand/icons/kapaat-logo.svg" width="96" alt="Kapaat logo">
</p>

<h1 align="center">Kapaat</h1>

<p align="center"><strong>Know what's in every bin.</strong></p>

<p align="center">
  Self-hosted home storage inventory: rooms › zones › bins › items, printable QR labels, and a phone app you install from the browser.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/backend-FastAPI-0ea5e9.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/frontend-React%20PWA-0ea5e9.svg" alt="React PWA">
  <img src="https://img.shields.io/badge/self--hosted-Docker-0ea5e9.svg" alt="Self-hosted">
</p>

<p align="center">
  4 label presets · 2 sign-in methods · AI photo entry · offline-readable PWA
</p>

<p align="center">
  <img src="docs/screenshots/home.png" width="320" alt="Kapaat home screen">
</p>

Kapaat (ਕਪਾਟ / कपाट — *cupboard*) is how you stop forgetting what's in the garage. Every bin gets a QR label; scan it with your phone to see what's inside, or search from anywhere.

## What it does

| | |
|---|---|
| **Rooms › zones › bins** | A room is an area of your home (Garage), a zone is part of it (North wall shelves), bins live in zones. |
| **Add items first, sort later** | Items don't need a bin. Put them in one when you get to it, or select many and bulk move them. |
| **Onboard and offboard** | Create bins and print their label in one step. Retire items and bins without losing history; restore any time. |
| **Check out / check in** | Track what's lent out or in use, with an optional due date and note. |
| **Labels that survive the garage** | Exact-size PDFs with a QR code — tape labels, Brother DK rolls, Avery sticker sheets, or plain paper with crop marks. |
| **Phone app (PWA)** | Install from the browser. Scan a label to open a bin, batch-move items by scanning, or check things back in. Works offline for reads. |
| **AI from photo** | Point the camera at an item; a configurable vision model fills in Name, Category, Notes and Tags for you to review. |
| **Simple sign-in** | A 6-digit code by email, plus optional passkeys and SSO (Authentik, Keycloak, Google…). |
| **Google Sheets mirror** | Optional webhook on every change; a copy-paste Apps Script keeps a spreadsheet in sync. |

## Workflows

Live captures from a running Kapaat instance.

**Add an item — manual.** Fill in a name and whatever else you know; everything but the name is optional. Tap the bin field to search and assign a bin in one step.

<p align="center">
  <img src="docs/screenshots/add-item-manual.png" width="260" alt="Add Item form filled in manually">
  <img src="docs/screenshots/bin-picker.png" width="260" alt="Bin picker sheet for assigning an item to a bin">
</p>

**Add an item — AI from photo.** Switch to AI mode, pick a photo; it's detecting while you wait, then Name/Category/Tags/Notes come back filled in for you to review before saving.

<p align="center">
  <img src="docs/screenshots/add-item-ai-detecting.png" width="260" alt="Add Item in AI from photo mode while detecting">
  <img src="docs/screenshots/add-item-ai-result.png" width="260" alt="Add Item in AI from photo mode with fields filled in">
</p>

**Add a bin.** Name it, place it in a room/zone, and optionally set a code and colour — then print its label right away.

<p align="center">
  <img src="docs/screenshots/add-bin.png" width="260" alt="Add Bin form">
</p>

**Item detail — check out, retire.** Every item page shows its bin and location, with one-tap check-out and a retire sheet that asks why (used up, donated, sold, thrown away, lost) instead of deleting outright.

<p align="center">
  <img src="docs/screenshots/item-detail.png" width="260" alt="Item detail page with Check out, Move, Retire actions">
  <img src="docs/screenshots/check-out.png" width="260" alt="Check-out sheet with optional due date and note">
  <img src="docs/screenshots/retire.png" width="260" alt="Retire sheet with reason options">
</p>

**Bin detail and bulk move.** A bin page lists its contents; from Home, Select lets you tick several items and move them all at once.

<p align="center">
  <img src="docs/screenshots/bin-detail.png" width="260" alt="Bin detail page listing its contents">
  <img src="docs/screenshots/bulk-select.png" width="260" alt="Home screen in bulk-select mode with a selection bar">
</p>

**Scan.** Open, move-into-bin and check-in modes, driven by the phone's camera reading a bin or item label.

<p align="center">
  <img src="docs/screenshots/scan.png" width="260" alt="Scan screen with Open / Move into bin / Check in modes">
</p>

**Print labels.** Pick a size — including the Avery 8163 sheet above — and which bins to print.

<p align="center">
  <img src="docs/screenshots/labels.png" width="260" alt="Print labels screen">
  <img src="docs/screenshots/places.png" width="260" alt="Places screen listing rooms and zones">
</p>

## Before you set this up

**Do I need a domain or reverse proxy?** No, to try it locally on the default port. Camera scanning and passkeys need HTTPS, so for daily use put Kapaat behind a reverse proxy (Caddy, Traefik, Nginx Proxy Manager…).

**Do I need email/SMTP configured?** No. The default `MAIL_BACKEND=log` prints sign-in codes to `docker compose logs api`, which is enough to try it out. Set `SMTP_*` to actually email codes.

**Can I migrate from v1?** Yes — see [Upgrading from v1](#upgrading-from-v1). Old QR labels keep working.

**Does the AI photo feature require a cloud API key?** No. It works with any OpenAI-compatible endpoint, including a self-hosted one; it's entirely optional and off by default.

## Install

You need Docker with Compose.

```bash
mkdir kapaat && cd kapaat
curl -fsSLO https://raw.githubusercontent.com/nomi25home/kapaat/main/docker-compose.yml
curl -fsSL https://raw.githubusercontent.com/nomi25home/kapaat/main/.env.example -o .env

# fill in the three required values
sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$(openssl rand -base64 48 | tr -d '\n')|" .env
sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(openssl rand -hex 24)|" .env
nano .env   # set BASE_URL to the address you'll open, and ADMIN_EMAIL to your email

docker compose up -d
```

Open `BASE_URL` (default port **8099**), enter your email, and sign in with the code. The first person to sign in becomes the admin; if `ADMIN_EMAIL` is set, only that address can.

Then: **Places** → add rooms and zones → **Add → Bin** → print its label → **Add → Item**.

To install the app on a phone, open Kapaat in the browser and use *Add to Home Screen* (iOS: Share menu; Android: browser menu).

### Printing labels

Print the PDF at **100% / actual size** (turn off "fit to page").

| Preset | Size | Use with |
|---|---|---|
| 48 mm tape label (default) | 48 × 30 mm, one per page | label makers, or print and trim; cover with 48 mm clear tape |
| Brother DK 62 mm | 62 × 29 mm | Brother QL printers with DK continuous rolls |
| A4 / Letter plain paper | 48 × 30 mm, 24 (A4) or 21 (Letter) per sheet | any inkjet or laser; cut along the crop marks |
| Avery L7160 / 5160 / 8163 | 63.5 × 38.1 mm / 66.7 × 25.4 mm / 101.6 × 50.8 mm | sticker sheets; "skip used positions" reuses partly used sheets |

### Back up

```bash
docker compose exec db pg_dump -U kapaat kapaat | gzip > kapaat-$(date +%F).sql.gz
docker run --rm -v kapaat_kapaat_photos:/p -v "$PWD":/out alpine tar czf /out/kapaat-photos-$(date +%F).tgz -C /p .
```

Restore into a fresh install: start only the database (`docker compose up -d db`), then `gunzip -c kapaat-….sql.gz | docker compose exec -T db psql -U kapaat kapaat`, unpack the photos into the `kapaat_photos` volume, and `docker compose up -d`. Practise this on a test install, not your live one.

### Upgrading from v1

See the [v2.0.0 release notes](docs/release-notes/v2.0.0.md) and [docs/migration-from-v1.md](docs/migration-from-v1.md). Old QR labels keep working. v1 images stay available as `ghcr.io/nomi25home/kapaat:1`.

## Configuration

All settings live in `.env`; [.env.example](.env.example) explains each one.

| Variable | Required | Purpose |
|---|---|---|
| `BASE_URL` | yes | Public address, used in QR codes and passkeys |
| `SECRET_KEY` | yes | Session signing key (≥ 32 chars) |
| `POSTGRES_PASSWORD` | yes | Database password |
| `ADMIN_EMAIL` | recommended | Only this address can claim the first admin account |
| `MAIL_BACKEND`, `SMTP_*` | for email | `log` prints codes to the API log; `smtp` sends them |
| `OPEN_SIGNUP` | no | Let anyone sign up instead of invite-only |
| `COOKIE_SECURE` | behind HTTPS | Mark the session cookie HTTPS-only |
| `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET` | no | Single sign-on; redirect URI is `BASE_URL/api/auth/oidc/callback` |
| `OIDC_ADMIN_GROUP` | no | Group whose members become admins |
| `WEBAUTHN_RP_ID` | no | Hostname of `BASE_URL`; turns on passkeys |
| `VISION_API_BASE`, `VISION_API_KEY`, `VISION_MODEL` | no | OpenAI-compatible vision endpoint; enables "AI from photo" mode on Add Item, which fills in Name/Category/Notes/Tags from a photo |
| `KAPAAT_PORT` | no | Host port (default 8099) |

## API

Interactive docs are at `BASE_URL/api/docs`. Create a token under **More → API tokens** and send it as `Authorization: Bearer kpt_…`. Read tokens can only `GET`.

```bash
curl -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/items?q=drill"
curl -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
     -d '{"item_ids":[3,4],"bin_id":12}' "$BASE_URL/api/items/move"
```

## Development

```
backend/    FastAPI + SQLAlchemy + Alembic (Python 3.13, uv)
frontend/   React + Vite PWA (TypeScript)
brand/      logo, icons, colour tokens
docs/       guides
```

```bash
# backend (needs a local Postgres; tests refuse to run unless the DB name contains "test")
cd backend && uv sync
export DATABASE_URL=postgresql+psycopg://kapaat:kapaat@localhost/kapaat_dev SECRET_KEY=dev-only-0123456789abcdef0123456789
uv run alembic upgrade head && uv run uvicorn app.main:app --reload
DATABASE_URL=postgresql+psycopg://kapaat:kapaat@localhost/kapaat_test uv run pytest

# frontend (proxies /api to localhost:8000)
cd frontend && npm ci && npm run dev
npm run typecheck && npm test
```

## Documentation

- [CONTRIBUTING](.github/CONTRIBUTING.md) — how to send a change
- [SECURITY](.github/SECURITY.md) — reporting a vulnerability
- [Design system](DESIGN.md) — how Kapaat looks and behaves
- [Roadmap](ROADMAP.md) — what's planned
- [Release test plan](docs/release-test-plan.html) — open in a browser to tick off checks
- [Migrating from v1](docs/migration-from-v1.md) · [v2.0.0 release notes](docs/release-notes/v2.0.0.md)
- [Google Sheets webhook setup](docs/sheets-webhook.md)

## License

[MIT](LICENSE)
