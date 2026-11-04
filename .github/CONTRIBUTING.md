# Contributing

Thanks for your interest in improving Kapaat! This document explains how to contribute effectively.

## Getting started locally

You need Python 3.13 with [uv](https://docs.astral.sh/uv/), Node 22, and a local Postgres.

```bash
git clone https://github.com/nomi25home/kapaat.git && cd kapaat
cd backend && uv sync
export DATABASE_URL=postgresql+psycopg://kapaat:kapaat@localhost/kapaat_dev SECRET_KEY=dev-only-0123456789abcdef0123456789
uv run alembic upgrade head && uv run uvicorn app.main:app --reload   # API on :8000, codes printed to the log
cd ../frontend && npm ci && npm run dev                                  # app on :5173, proxies /api
```

Tests use their own database and refuse to run unless its name contains `test`:

```bash
cd backend && DATABASE_URL=postgresql+psycopg://kapaat:kapaat@localhost/kapaat_test uv run pytest
uv run ruff check . && uv run ruff format --check .
cd ../frontend && npm run typecheck && npm test
```

Schema changes need an Alembic migration: `uv run alembic revision --autogenerate -m "…"`, then review it.

## Reporting bugs

1. Search [existing issues](https://github.com/nomi25home/kapaat/issues) first.
2. Open a new issue using the **Bug report** template.
3. Include: steps to reproduce, expected vs actual behaviour, browser/OS, and any relevant console errors.

## Suggesting features

Open a [Feature request](https://github.com/nomi25home/kapaat/issues/new) issue before writing code. Briefly describe the use-case and proposed approach. This avoids wasted effort if the direction doesn't fit the project.

## Submitting a Pull Request

1. **Fork** the repo and create a feature branch off `main`:
   ```bash
   git checkout -b feat/my-feature
   ```
2. **Keep changes focused** — one feature or fix per PR. Unrelated cleanups belong in a separate PR.
3. **Test your change** manually against a local instance before opening the PR.
4. **Update `CHANGELOG.md`** — add a line under `[Unreleased]` describing what changed.
5. **Open the PR** against `main`. Fill in the description with *what* changed and *why*.

### PR checklist

- [ ] No hardcoded secrets, IPs, or personal URLs
- [ ] New configuration values are exposed via environment variables and documented in `.env.example`
- [ ] UI changes are tested in light and dark mode at phone (390 px) and desktop widths
- [ ] Backend changes have tests; `pytest`, `ruff`, `npm run typecheck` and `npm test` pass
- [ ] No new runtime dependencies added without discussion (keep the image lean)

## Code style

- Python: formatted and linted by ruff; keep routers thin and put shared logic in `app/services/`.
- TypeScript/React: strict mode; data fetching through the hooks in `src/api/hooks.ts`; styles use the tokens in `src/styles.css`.

## Commit messages

Use the conventional format: `type: short summary` (e.g. `feat: add room filter`, `fix: bin edit modal typo`, `docs: update README`). No period at the end.
