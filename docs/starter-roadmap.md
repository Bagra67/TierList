# Roadmap: finishing the TierList starter

English | [Français](starter-roadmap.fr.md)

This document lists what is missing to **bootstrap** the project properly, before developing the first feature. It contains no business feature: only tooling, quality and organization.

## Current state

- **Backend** FastAPI: `GET /hello`, plus `GET /health/db`, wired to PostgreSQL (SQLAlchemy 2, psycopg 3, Alembic).
- **Database** PostgreSQL 18 in Docker (`compose.yaml`).
- **Frontend** React + TypeScript (Vite): displays the "Hello World" returned by the backend.
- **Tooling**: uv, pnpm, Ruff, ESLint, Prettier, husky pre-commit hook, `dev.*` scripts.

Identified gaps:
- no remote repository;
- no CI;
- no Python type checking;
- no frontend tests;
- `strict` is not set explicitly in `tsconfig.app.json`.

Each item below states what is missing, why it is useful and what to do. Each one will be a separate commit, with the related README updated.

---

## P1: required before the first feature

1. **Commit the current state and add a remote repository.**
   - Make coherent commits: back to Hello World, `dev.*` scripts, PostgreSQL and SQLAlchemy.
   - Add a remote repository (GitHub?). Without it, nothing is backed up or shareable.

2. **CI (GitHub Actions)**: a workflow on every push and every PR, with two jobs.
   - backend: `uv sync --locked`, `ruff check`, `ruff format --check`, `pytest`;
   - frontend: `pnpm install --frozen-lockfile`, `lint`, `format:check`, `typecheck`, `build`.

   The pre-commit hook is easy to bypass. CI is the real safeguard.

3. **Python type checking**: add **Pyright** (or mypy) to the dev group, in `standard` mode, then to CI and the README. AGENTS.md requires type hints, but nothing checks them today.

4. **Frontend tests**: **Vitest + Testing Library + jsdom**, configured in `vite.config.ts`, plus a `pnpm test` script.
   - A first test covers the 3 states of `App`: loading, message and error, by mocking `fetch`.
   - Today, the frontend has no tests at all.

5. **Backend integration tests against a real PostgreSQL.** `/health/db` is only tested with SQLite or a fake object.
   - Add a separate test database, e.g. `tierlist_test` on the same container.
   - Add a pytest fixture that applies the Alembic migrations, then isolates each test in a transaction rolled back at the end.
   - Add an `integration` marker, with a PostgreSQL service in CI.

   This is the foundation every future database-related feature will need.

6. **Configure backend logging**: level set through an environment variable (`LOG_LEVEL`) and a format consistent with uvicorn's. For now, `logger.exception` only shows up thanks to Python's last-resort handler.

## P2: strongly recommended

7. **Pin tool versions**, so that every machine and CI use the same ones:
   - `packageManager` (pnpm) and `engines.node` fields in `package.json`;
   - `.nvmrc` file;
   - `strict: true` set explicitly in `tsconfig.app.json`.

8. **End-to-end typed API contract**: generate the TypeScript types from FastAPI's OpenAPI, with `openapi-typescript` and a `pnpm gen:api` script.
   - CI checks that the generated types are up to date.
   - Today, `HelloResponse` is copied by hand on the frontend, while AGENTS.md §23 requires this contract to stay in sync.

9. **Choose the frontend data-fetching layer**: **TanStack Query** on top of a small shared `fetch` client (consistent base URL and error handling).
   - Otherwise, every feature will reinvent its own `useEffect`, which AGENTS.md §17 discourages.
   - *This decision needs to be validated.*

10. **Single error format on the backend**: global handlers for unexpected exceptions (generic, logged 500 response) and for validation errors, all in the same JSON format. The frontend can then handle them all the same way.

11. **Split the health probes**: `/health` only checks that the application responds, `/health/db` that the database is reachable. Docker or a hosting platform uses the first one, troubleshooting the second one.

12. **Start the database from the dev scripts**: `dev.sh` and `dev.ps1` would run `docker compose up -d --wait` before the servers. The message would be clear if Docker is not running, and an option would allow skipping this step.

13. **Automatic dependency updates** with Dependabot or Renovate, for uv, pnpm, GitHub Actions and the Docker image. Updates arrive as PRs, and CI validates them.

## P3: comfort and hygiene

14. **`.editorconfig`**: LF, UTF-8 and indentation, for editors other than VS Code.

15. **VS Code**:
    - `launch.json` to debug FastAPI and Vitest (it must be allowed in `.gitignore`);
    - add the Docker extension to the recommendations.

16. **Secret scanning** before each commit, with gitleaks in the pre-commit hook, on top of `.gitignore`.

17. **Test coverage**: `pytest-cov` and `vitest --coverage`, with a report in CI but no blocking threshold at first.

18. **Documentation**:
    - a short `docs/architecture.md`: layers, front → API → service → repository → DB flow, conventions;
    - a PR template (`.github/pull_request_template.md`) based on the AGENTS.md checklist.

19. **Standardized commit messages** (Conventional Commits, checked by commitlint in husky). Useful for an automatic changelog. Optional.

## Deliberately not proposed (for now)

These items are postponed (YAGNI):
- **Production Dockerfiles and deployment**: to do once a hosting target is chosen.
- **Authentication, frontend routing (react-router), UI library**: these choices depend on the features.
- **Reorganizing `main.py` into `api/routes/` and services**: to do with the first real resource, not before.

---

## Checking each item

- Backend: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, plus Pyright once added.
- Frontend: `pnpm lint`, `pnpm format:check`, `pnpm typecheck`, `pnpm build`, plus `pnpm test` once added.
- End to end: `docker compose up -d --wait`, then `GET /health/db` must return `{"status":"ok"}`.
- CI: push a branch and check that the jobs pass (`gh run watch`).
