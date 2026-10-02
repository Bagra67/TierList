# Roadmap: finishing the TierList starter

English | [Français](starter-roadmap.fr.md)

This document lists what is missing to **bootstrap** the project properly, before developing the first feature. It contains no business feature: only tooling, quality and organization.

## Current state

- **Backend** FastAPI: `GET /hello`, health probes `GET /health` (liveness) and `GET /health/db` (database), wired to PostgreSQL (SQLAlchemy 2, psycopg 3, Alembic).
- **Database** PostgreSQL 18 in Docker (`compose.yaml`).
- **Frontend** React + TypeScript (Vite): displays the "Hello World" returned by the backend.
- **Logging**: application logs configured with `LOG_LEVEL`, in uvicorn's format.
- **Errors**: single JSON error format (`ErrorResponse`) for HTTP, validation and unexpected errors; read by the frontend's `ApiError`.
- **API contract**: `backend/openapi.json` exported and checked; frontend API types generated from it (`pnpm gen:api`).
- **Data fetching**: TanStack Query on top of a shared openapi-fetch client typed by the API contract.
- **Tooling**: uv, pnpm, Ruff, Pyright, ESLint, Prettier (also on `docs/`), EditorConfig, VS Code debug configurations (FastAPI, Vitest), husky pre-commit hook (with gitleaks secret scanning, also on CI) and commit-msg hook (commitlint), `dev.*` scripts (start the database, then both servers); Node and pnpm versions pinned.
- **Tests**: pytest (unit + integration against a real PostgreSQL), Vitest + Testing Library, coverage reports.
- **Documentation**: architecture (`docs/architecture.md`), testing guide, roadmap; English and French.
- **CI**: GitHub Actions (`Backend` and `Frontend` jobs, required on `develop` and `main`), Dependabot, pull request template; merged work branches are deleted automatically.

Completed items have been removed from this list; the remaining ones keep their original number.

Each item below states what is missing, why it is useful and what to do. Each one will be a separate commit, with the related README updated.

---

## P1: required before the first feature

All P1 items are done.

## P2: strongly recommended

All P2 items are done.

## P3: comfort and hygiene

All P3 items are done.

## Deliberately not proposed (for now)

These items are postponed (YAGNI):

- **Production Dockerfiles and deployment**: to do once a hosting target is chosen.
- **Authentication, frontend routing (react-router), UI library**: these choices depend on the features.
- **Reorganizing `main.py` into `api/routes/` and services**: to do with the first real resource, not before.

---

## Checking each item

- Backend: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`.
- Frontend: `pnpm lint`, `pnpm format:check`, `pnpm typecheck`, `pnpm test`, `pnpm build`.
- End to end: `docker compose up -d --wait`, then `GET /health` and `GET /health/db` must return `{"status":"ok"}`.
- CI: push a branch and check that the jobs pass (`gh run watch`).
