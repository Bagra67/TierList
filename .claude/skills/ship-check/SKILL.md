---
name: ship-check
description: Run locally every check the CI runs (backend, frontend, docs) plus the AGENTS.md review checklist, and report the results as the AGENTS.md §49 validation table. Use before marking a PR ready or before the final report of a task.
---

# Ship check

Runs the same checks as `.github/workflows/ci.yml` and `docs.yml`, so a PR does not discover them on
GitHub. Never report a check as passing without having run it (AGENTS.md §2, §49).

## 1. Scope

Find the changed parts against the PR base (`develop`, or the branch below in a stack):

```bash
git diff --name-only origin/develop...HEAD
git status --short
```

Run the backend checks only if `backend/` changed, the frontend checks only if `frontend/` or
`backend/openapi.json` changed. The docs checks always run.

## 2. Backend (from `backend/`)

The integration tests need PostgreSQL and SeaweedFS: start them first from the repo root with
`docker compose up -d --wait`. If Docker is not available, run `uv run pytest -n auto -m "not
integration"` and report the integration tests as NOT RUN.

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest -n auto
```

## 3. Frontend (from `frontend/`)

```bash
pnpm gen:api && git diff --exit-code -- src/api/schema.d.ts
pnpm lint
pnpm format:check
pnpm typecheck
pnpm knip
pnpm test
pnpm build
pnpm test:e2e
```

If `gen:api` changes `schema.d.ts`, the API types were out of date: use `/api-sync`.

`pnpm test:e2e` runs the Playwright tests on the build, on Chromium, Firefox and WebKit. It needs
`docker compose up -d --wait` and the browsers (`pnpm exec playwright install chromium firefox
webkit`); without them, report it as NOT RUN with the reason.

## 4. Docs (from the repo root)

```bash
python -m unittest discover -s .github/scripts
python .github/scripts/check_docs_sync.py --base origin/develop
```

## 5. Browser check (frontend changes only)

If `frontend/src/` changed and the app runs locally (`dev.*`, with `docker compose up -d --wait`),
use the `playwright` MCP server to walk through the screens the PR touches on
`http://127.0.0.1:5173`: the main flow, the loading, error and empty states, the page in French and
in English, and `browser_console_messages` for errors. Report it as one line of the table. If the
app is not running, report it as NOT RUN with the reason: never start it against staging or
production.

## 6. Review checklist

Read the diff (`git diff origin/develop...HEAD`) and answer each point with yes, no or not concerned:

- Tests added or updated for the new behavior, and the testing guide updated (§28).
- Every new user-facing text goes through `t()` and exists in `fr.ts` and `en.ts`; every new
  `ErrorCode` is translated under `errors.*` (§50).
- Privacy policy: does the change touch personal data, retention, a provider, a cookie or a storage
  key, or what other users see (§51)?
- Seed data: does `backend/app/seed/` need to cover the new data or cases (§28)?
- Schema change: an Alembic migration exists and was reviewed (§36).
- READMEs changed in both `README.md` and `README.fr.md` (§31).
- No comment that only repeats the code (§31), no unrelated change (§5).

## Report

Give the §49 table, one line per command actually run, then the checklist answers:

```text
ruff check                     PASS
pytest                         FAIL (2 failed: tests/test_x.py::test_y, ...)
pnpm build                     NOT RUN
Reason: ...
```

On a failure, show the relevant output and stop: do not mark the PR ready.
