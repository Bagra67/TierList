# TierList

English | [Français](README.fr.md)

TierList application made of two projects in a single git repository:

| Folder | Content | Tools |
| --- | --- | --- |
| [`backend/`](backend/README.md) | **FastAPI** API (Python 3.11+) + **PostgreSQL** (Docker) | uv, Ruff, pytest, SQLAlchemy, Alembic |
| [`frontend/`](frontend/README.md) | **React + TypeScript** with Vite | pnpm, ESLint, Prettier |

How the code is organized and where new code goes: [docs/architecture.md](docs/architecture.md). Accounts and sign-in: [docs/authentication.md](docs/authentication.md). Versions and releases (`develop` → `main`): [docs/releasing.md](docs/releasing.md), changes in [CHANGELOG.md](CHANGELOG.md).

```
TierList/
├── backend/            # FastAPI API  → see backend/README.md
├── frontend/           # React app    → see frontend/README.md
│   └── .husky/         # Git pre-commit hook (for the whole repository)
├── compose.yaml        # Development PostgreSQL database (Docker)
├── .github/            # CI workflow, Dependabot, pull request template
├── .vscode/            # Shared VS Code settings (format on save, debug configurations…)
├── .editorconfig       # Encoding, line endings, indentation for every editor
├── .nvmrc              # Node.js version (24)
├── dev.sh              # Runs backend + frontend in dev mode (Git Bash, macOS, Linux)
├── dev.cmd / dev.ps1   # Same for PowerShell / cmd
├── docs/               # Documentation (architecture, testing guide, releasing)
└── README.md / README.fr.md   # This file (English / French)
```

---

## 1. Prerequisites

| Tool | Installation | Check |
| --- | --- | --- |
| **uv** | Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"`<br>macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `uv --version` |
| **Node.js 24 LTS** (version in `.nvmrc`) | Windows: `winget install OpenJS.NodeJS.LTS` — or https://nodejs.org | `node --version` |
| **pnpm** | `npm install -g pnpm` | `pnpm --version` |
| **Git** | https://git-scm.com | `git --version` |
| **Docker Desktop** | Windows: `winget install -e --id Docker.DockerDesktop` (requires WSL2, may need a reboot), then start Docker Desktop once — or https://www.docker.com/products/docker-desktop | `docker info` |
| **gitleaks** (required by the pre-commit hook) | Windows: `winget install -e --id Gitleaks.Gitleaks` (then restart VS Code and the terminals)<br>macOS: `brew install gitleaks` — or https://github.com/gitleaks/gitleaks | `gitleaks version` |

---

## 2. Installation (after cloning)

```bash
cd backend
uv sync           # creates backend/.venv and installs the Python dependencies

cd ../frontend
pnpm install      # installs the JS dependencies and enables the git hook

cd ..
cp backend/.env.example backend/.env   # then change the password in backend/.env
```

`backend/.env` (not committed) holds the PostgreSQL credentials: it is read both by the backend and by the Docker container.

---

## 3. Running the application in development

### Database (PostgreSQL in Docker)

Docker Desktop must be running. From the `TierList/` root:

| Action | Command |
| --- | --- |
| Start the database (waits until it is ready) | `docker compose up -d --wait` |
| Show its status / logs | `docker compose ps` / `docker compose logs db` |
| Stop it (data is kept) | `docker compose down` |
| Reset everything (⚠️ **deletes the data**) | `docker compose down -v` |

The database keeps running in the background between dev sessions: no need to restart it every time. Check that the backend can reach it: http://127.0.0.1:8000/health/db → `{"status":"ok"}`.

### With a single command (recommended)

From the `TierList/` root, depending on your terminal:

| Terminal | Command |
| --- | --- |
| **Git Bash**, macOS, Linux | `./dev.sh` |
| PowerShell, cmd | `.\dev.cmd` |

Starts the backend (http://127.0.0.1:8000) and the frontend (http://localhost:5173) in the same terminal, with auto-reload. **Ctrl+C stops both.**

- On first run, the script installs the dependencies if needed (`uv sync`, `pnpm install`).
- It first starts the PostgreSQL database (`docker compose up -d --wait`) and waits until it is ready. If Docker Desktop is not running, it stops with a clear message. To start without the database: `./dev.sh --no-db` or `.\dev.cmd -NoDb`.
- If one of the two servers stops (error, crash…), the other one is stopped too.
- If port 8000 or 5173 is already in use, `dev.sh` refuses to start and tells you.
- In `dev.sh`, logs are prefixed with `[backend]` / `[frontend]`.

> ⚠️ In **Git Bash**, use `dev.sh`, not `dev.cmd`: Git Bash does not forward Ctrl+C properly to Windows scripts, and servers could keep running in the background.
> `.\dev.ps1` also works in PowerShell if script execution is allowed; `dev.cmd` bypasses that restriction for you.

### Separately, in two terminals

**Terminal 1 — backend** (http://127.0.0.1:8000, docs at `/docs`)
```bash
cd backend
uv run fastapi dev app/main.py
```

**Terminal 2 — frontend** (http://localhost:5173)
```bash
cd frontend
pnpm dev
```

The frontend displays the "Hello World" returned by the backend. It calls it through `/api/...` (Vite proxy → port 8000): no CORS configuration is needed in development.

---

## 4. Code quality (automatic)

**In VS Code**: when opening the `TierList` folder, accept installing the recommended extensions (ESLint, Prettier, Ruff, Python, Python Debugger, Docker). Code is then fixed and formatted **on every save**:
- `.ts` / `.tsx` / `.json` / `.css` → Prettier + ESLint
- `.py` → Ruff

**Debugging in VS Code** (`.vscode/launch.json`, **Run and Debug** view, then F5):
- **Backend: FastAPI** starts uvicorn on port 8000 under the debugger: breakpoints in `backend/app/` stop the request. No auto-reload in this mode; stop `dev.sh` first, as the port is the same.
- **Frontend: Vitest (current file)** runs the tests of the open test file with breakpoints in the tests and in `frontend/src/`.

**Before each commit**, the `frontend/.husky/pre-commit` git hook runs:
1. `gitleaks` on the staged changes: the commit is refused if they contain a secret (key, password, token). The output shows the file, line and rule, with the secret masked. A false positive can be ignored with a `gitleaks:allow` comment on the line;
2. `lint-staged` on the modified frontend files (ESLint `--fix` + Prettier);
3. `ruff check` and `ruff format --check` on the backend.

If an error cannot be fixed automatically, the commit is blocked: fix it, then commit again.

**Commit messages** are checked by the `frontend/.husky/commit-msg` hook (commitlint, `frontend/commitlint.config.js`): they must follow Conventional Commits, `type(scope): summary` (e.g. `feat(backend): add the tier list API`), with a lowercase summary and body lines of 100 characters at most. Allowed types: `build`, `chore`, `ci`, `docs`, `feat`, `fix`, `perf`, `refactor`, `revert`, `style`, `test`.

Manual commands:

| | Backend (`cd backend`) | Frontend (`cd frontend`) |
| --- | --- | --- |
| Lint | `uv run ruff check .` | `pnpm lint` |
| Fix | `uv run ruff check . --fix` | `pnpm lint:fix` |
| Format | `uv run ruff format .` | `pnpm format` |
| Types | `uv run pyright` | `pnpm typecheck` |
| Tests | `uv run pytest` | `pnpm test` |
| Tests + coverage | `uv run pytest --cov=app` | `pnpm test:coverage` |

Backend integration tests need the database: `docker compose up -d --wait` (otherwise they are skipped locally). How each test works and what it checks: [docs/testing.md](docs/testing.md).

### Continuous integration (GitHub Actions)

`.github/workflows/ci.yml` runs on every pull request (including stacked PRs based on another work branch) and every push to `develop` and `main`:

| Job | Steps |
| --- | --- |
| **Backend** | `uv sync --locked`, Ruff (lint + format), Pyright, pytest with coverage against a PostgreSQL 18 service |
| **Frontend** | `pnpm install --frozen-lockfile`, ESLint, Prettier, `tsc`, Vitest with coverage, production build |
| **Secrets** | gitleaks on every commit of the PR (or of the push) |

- The run summary shows a **test report** for each job (result and duration of every test, failure details, skip reasons, slowest tests) and the coverage (no blocking threshold). Raw reports are kept as artifacts for 14 days. See [docs/testing.md](docs/testing.md#31-test-report-on-ci).
- The three jobs (`Backend`, `Frontend`, `Secrets`) are **required checks** on `develop` and `main`: a PR cannot be merged while CI fails.
- **Dependabot** (`.github/dependabot.yml`) opens weekly update PRs against `develop` for uv, pnpm, GitHub Actions and the Docker image.
- New PRs are pre-filled by `.github/pull_request_template.md`.

---

## 5. Adding a package

| | Backend (`cd backend`) | Frontend (`cd frontend`) |
| --- | --- | --- |
| Dependency | `uv add <package>` | `pnpm add <package>` |
| Dev dependency | `uv add --dev <package>` | `pnpm add -D <package>` |
| Remove | `uv remove <package>` | `pnpm remove <package>` |

More details in [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md).

---

## 6. Git

- A single repository for the whole project, main branch `main`.
- Commit the lock files (`backend/uv.lock`, `frontend/pnpm-lock.yaml`).
- `.venv/`, `node_modules/` and `dist/` are ignored.
- After a `git pull`: run `uv sync` in `backend/` and `pnpm install` in `frontend/` if dependencies changed.
- To publish on GitHub: create an empty repository, then
  ```bash
  git remote add origin https://github.com/<user>/TierList.git
  git push -u origin main
  ```

---

## 7. License

Proprietary code, **all rights reserved**: no reuse, copying, modification or redistribution without the author's written permission. See [LICENSE](LICENSE).
