# Kapaat

<img src="brand/icons/kapaat-logo.svg" width="72" align="right" alt="Kapaat logo">

**Know what's in every bin.** Kapaat (ਕਪਾਟ / कपाट — *cupboard*) is a self-hosted home storage inventory: rooms › zones › bins › items, printable QR labels, and a phone app you install from the browser.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## What it does

- **Rooms › zones › bins.** A room is an area of your home (Garage), a zone is part of it (North wall shelves), bins live in zones.
- **Add items first, sort later.** Items don't need a bin. Put them in one when you get to it, or select many and **bulk move** them.
- **Onboard and offboard.** Create bins and print their label in one step. Retire items (used up, donated, sold…) and bins (move their contents or take them out) without losing history; restore any time.
- **Check out / check in.** Track what's lent out or in use, with an optional due date and note.
- **Labels that survive the garage.** Exact-size PDFs with a QR code: **48 mm × 30 mm** by default, sized to sit under 48 mm clear packing tape. Also Brother DK 62 mm, Avery L7160 (A4) and 5160 (Letter) sticker sheets, and plain A4/Letter paper with crop marks for cutting.
- **Phone app (PWA).** Install from the browser. Scan a label with the camera to open a bin, batch-move items by scanning, or check things back in. Your last-seen inventory stays readable offline.
- **Simple sign-in.** A 6-digit code by email. Optionally add passkeys (Face ID, Touch ID, device PIN) and single sign-on (Authentik, Keycloak, Google…).
- **Google Sheets mirror (optional).** Every change can be sent to a webhook; a [copy-paste Apps Script](docs/sheets-webhook.md) keeps a spreadsheet in sync. Works with n8n, Home Assistant or your own code too.
- Photos, tags, CSV export, per-person API tokens.

## Run it

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

Open `BASE_URL` (default port **8099**), enter your email, and sign in with the code. With the default `MAIL_BACKEND=log` the code is printed in `docker compose logs api`; set the `SMTP_*` values to email it instead. The first person to sign in becomes the admin; if `ADMIN_EMAIL` is set, only that address can.

Then: **Places** → add rooms and zones → **Add → Bin** → print its label → **Add → Item**.

To install the app on a phone, open Kapaat in the browser and use *Add to Home Screen* (iOS: Share menu; Android: browser menu). Camera scanning and passkeys need HTTPS, so put Kapaat behind your reverse proxy (Caddy, Traefik, Nginx Proxy Manager…) and set `COOKIE_SECURE=true`.

### Printing labels

Print the PDF at **100% / actual size** (turn off "fit to page").

| Preset | Size | Use with |
|---|---|---|
| 48 mm tape label (default) | 48 × 30 mm, one per page | label makers, or print and trim; cover with 48 mm clear tape |
| Brother DK 62 mm | 62 × 29 mm | Brother QL printers with DK continuous rolls |
| A4 / Letter plain paper | 48 × 30 mm, 24 (A4) or 21 (Letter) per sheet | any inkjet or laser; cut along the crop marks |
| Avery L7160 / 5160 | 63.5 × 38.1 mm / 66.7 × 25.4 mm | sticker sheets; "skip used positions" reuses partly used sheets |

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

See [CONTRIBUTING](.github/CONTRIBUTING.md), [SECURITY](.github/SECURITY.md), the [design system](DESIGN.md), the [roadmap](ROADMAP.md), and the [release test plan](docs/release-test-plan.html) (open it in a browser to tick off checks).

## License

[MIT](LICENSE)
