# Roadmap: finishing the TierList starter

English | [Français](starter-roadmap.fr.md)

This document lists what is missing to **bootstrap** the project properly, before developing the first feature. It contains no business feature: only tooling, quality and organization.

## Current state

- **Backend** FastAPI: `GET /hello`, plus `GET /health/db`, wired to PostgreSQL (SQLAlchemy 2, psycopg 3, Alembic).
- **Database** PostgreSQL 18 in Docker (`compose.yaml`).
- **Frontend** React + TypeScript (Vite): displays the "Hello World" returned by the backend.
- **Logging**: application logs configured with `LOG_LEVEL`, in uvicorn's format.
- **API contract**: `backend/openapi.json` exported and checked; frontend API types generated from it (`pnpm gen:api`).
- **Data fetching**: TanStack Query on top of a shared openapi-fetch client typed by the API contract.
- **Tooling**: uv, pnpm, Ruff, Pyright, ESLint, Prettier, husky pre-commit hook, `dev.*` scripts; Node and pnpm versions pinned.
- **Tests**: pytest (unit + integration against a real PostgreSQL), Vitest + Testing Library, coverage reports.
- **CI**: GitHub Actions (`Backend` and `Frontend` jobs, required on `develop` and `main`), Dependabot, pull request template.

Completed items have been removed from this list; the remaining ones keep their original number.

Each item below states what is missing, why it is useful and what to do. Each one will be a separate commit, with the related README updated.

---

## P1: required before the first feature

All P1 items are done.

## P2: strongly recommended

10. **Single error format on the backend**: global handlers for unexpected exceptions (generic, logged 500 response) and for validation errors, all in the same JSON format. The frontend can then handle them all the same way.

11. **Split the health probes**: `/health` only checks that the application responds, `/health/db` that the database is reachable. Docker or a hosting platform uses the first one, troubleshooting the second one.

12. **Start the database from the dev scripts**: `dev.sh` and `dev.ps1` would run `docker compose up -d --wait` before the servers. The message would be clear if Docker is not running, and an option would allow skipping this step.

## P3: comfort and hygiene

14. **`.editorconfig`**: LF, UTF-8 and indentation, for editors other than VS Code.

15. **VS Code**:
    - `launch.json` to debug FastAPI and Vitest (it must be allowed in `.gitignore`);
    - add the Docker extension to the recommendations.

16. **Secret scanning** before each commit, with gitleaks in the pre-commit hook, on top of `.gitignore`.

<!-- 17 done: list restarts at 18 to keep the original numbers -->

18. **Documentation**:
    - a short `docs/architecture.md`: layers, front → API → service → repository → DB flow, conventions.

19. **Enforce commit messages**: Conventional Commits are now the rule (AGENTS.md §39); commitlint in husky would check them automatically. Useful for an automatic changelog. Optional.

## Deliberately not proposed (for now)

These items are postponed (YAGNI):
- **Production Dockerfiles and deployment**: to do once a hosting target is chosen.
- **Authentication, frontend routing (react-router), UI library**: these choices depend on the features.
- **Reorganizing `main.py` into `api/routes/` and services**: to do with the first real resource, not before.

---

## Checking each item

- Backend: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`.
- Frontend: `pnpm lint`, `pnpm format:check`, `pnpm typecheck`, `pnpm test`, `pnpm build`.
- End to end: `docker compose up -d --wait`, then `GET /health/db` must return `{"status":"ok"}`.
- CI: push a branch and check that the jobs pass (`gh run watch`).
