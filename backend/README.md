# TierList — FastAPI backend

English | [Français](README.fr.md)

Python backend built with [FastAPI](https://fastapi.tiangolo.com/), managed with the [uv](https://docs.astral.sh/uv/) package and project manager.

> This folder is part of the [TierList](../README.md) repository. **All commands below are run from the `backend/` folder** (`cd backend`).

---

## 1. Prerequisites

- **uv** (it installs and manages Python itself if needed)
- Python **3.11+** (version pinned in `.python-version`)

### Installing uv

**Windows (PowerShell)**:
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS / Linux**:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then restart your terminal and check:
```bash
uv --version
```

---

## 2. Installing the project

From the `backend/` folder:
```bash
uv sync
```

This command:
- creates the `.venv/` virtual environment if it does not exist;
- installs all dependencies (dev ones included) at the exact versions of `uv.lock`.

### Activating the virtual environment (optional)

With `uv run`, activation is **not needed**: uv uses `.venv` automatically.
If you still want to activate it (e.g. to call `python` or `fastapi` directly):

| System | Command |
|---|---|
| Windows (PowerShell) | `.venv\Scripts\Activate.ps1` |
| Windows (cmd) | `.venv\Scripts\activate.bat` |
| macOS / Linux | `source .venv/bin/activate` |

To deactivate it: `deactivate`.

> VS Code is already configured (`.vscode/settings.json` at the root) to use `backend/.venv`. Otherwise: `Ctrl+Shift+P` → *Python: Select Interpreter*.

---

## 3. Running the server

**Development mode** (auto-reload on every change):
```bash
uv run fastapi dev app/main.py
```

**Production mode**:
```bash
uv run fastapi run app/main.py
```

Change the port / host:
```bash
uv run fastapi dev app/main.py --port 8080 --host 0.0.0.0
```

Once running:
- API: http://127.0.0.1:8000
- Interactive documentation (Swagger): http://127.0.0.1:8000/docs
- ReDoc documentation: http://127.0.0.1:8000/redoc

The frontend calls the backend through the Vite proxy: a request to `http://localhost:5173/api/hello` is forwarded to `http://127.0.0.1:8000/hello`. The backend must therefore run on port **8000** during frontend development.

---

## 4. Managing packages

> ⚠️ Do not use `pip install` directly: always go through `uv` so that `pyproject.toml` and `uv.lock` stay up to date.

| Action | Command |
|---|---|
| Add a package | `uv add <package>` (e.g. `uv add sqlalchemy`) |
| Add a specific version | `uv add "sqlalchemy>=2.0"` |
| Add a dev package (tests, lint…) | `uv add --dev <package>` (e.g. `uv add --dev ruff`) |
| Remove a package | `uv remove <package>` |
| Upgrade a package | `uv lock --upgrade-package <package>` then `uv sync` |
| Upgrade all packages | `uv lock --upgrade` then `uv sync` |
| Show the dependency tree | `uv tree` |
| List installed packages | `uv pip list` |
| Reinstall from the lockfile | `uv sync` |
| Install without dev dependencies (prod) | `uv sync --no-dev` |

Run any command inside the project environment:
```bash
uv run python script.py
uv run <command>
```

---

## 5. Tests

```bash
uv run pytest
```

Verbose mode: `uv run pytest -v` — with coverage: `uv run pytest --cov=app`

### Integration tests (real PostgreSQL)

Tests under `tests/integration/` (marker `integration`) run against a real PostgreSQL:

- Start the database first: `docker compose up -d --wait` (from the repository root).
- They use a dedicated `<POSTGRES_DB>_test` database (e.g. `tierlist_test`), created automatically, with the Alembic migrations applied: **development data is never touched**.
- Each test runs in a transaction that is rolled back at the end.
- If PostgreSQL is not reachable, they are **skipped** locally, but they **fail** on CI.

| Action | Command |
|---|---|
| Unit tests only | `uv run pytest -m "not integration"` |
| Integration tests only | `uv run pytest -m integration` |

---

## 6. Lint and formatting (Ruff)

[Ruff](https://docs.astral.sh/ruff/) is both the linter and the formatter. It is configured in `pyproject.toml` (`[tool.ruff]` section).

| Action | Command |
|---|---|
| Analyze the code | `uv run ruff check .` |
| Fix automatically | `uv run ruff check . --fix` |
| Format the code | `uv run ruff format .` |
| Check formatting without changing files (CI) | `uv run ruff format . --check` |

The `pre-commit` git hook (see the [root README](../README.md)) automatically runs `ruff check` and `ruff format --check` before each commit. To fix things before committing:
```bash
uv run ruff check . --fix && uv run ruff format .
```

> In VS Code, install the **Ruff** extension (`charliermarsh.ruff`) to get linting and formatting on save.

### Type checking (Pyright)

```bash
uv run pyright
```

Configured in `pyproject.toml` (`[tool.pyright]`, `standard` mode, on `app/`, `tests/` and `migrations/`). Also run by CI.

---

## 7. Project structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI entry point (GET /hello, GET /health/db)
│   ├── core/
│   │   ├── config.py      # Configuration read from .env (pydantic-settings)
│   │   └── logging.py     # Application logging (LOG_LEVEL, uvicorn format)
│   └── db/
│       ├── base.py        # Base class for SQLAlchemy models
│       └── session.py     # Engine, session (FastAPI dependency), database ping
├── migrations/            # Alembic migrations (env.py, versions/)
├── tests/
│   ├── test_main.py       # Unit tests with TestClient (no real database)
│   └── integration/       # Tests against a real PostgreSQL (database <POSTGRES_DB>_test)
├── .env.example           # .env template (PostgreSQL credentials)
├── alembic.ini            # Alembic configuration
├── .python-version        # Python version used by uv
├── pyproject.toml         # Project metadata + dependencies
├── uv.lock                # Exact locked versions (to commit)
└── README.md / README.fr.md   # This file (English / French)
```

---

## 8. Good practices

- **Commit** `pyproject.toml`, `uv.lock` and `.python-version`.
- **Do not commit** `.venv/` (already in `.gitignore`).
- After a `git pull`, run `uv sync` to get up to date.
- Change the Python version: `uv python pin 3.12` then `uv sync`.
- **Do not commit** `.env`: only `.env.example` is versioned.

---

## 9. Database (PostgreSQL + SQLAlchemy + Alembic)

The database runs in Docker (`compose.yaml` at the repository root, see the [root README](../README.md)). The backend connects to it with **SQLAlchemy 2** and the **psycopg 3** driver.

### Configuration

Copy `.env.example` to `.env` (in `backend/`) and adjust the values:

| Variable | Purpose | Default |
|---|---|---|
| `POSTGRES_USER` | User | — (required) |
| `POSTGRES_PASSWORD` | Password | — (required) |
| `POSTGRES_DB` | Database name | — (required) |
| `POSTGRES_HOST` | Host as seen from the backend | `127.0.0.1` |
| `POSTGRES_PORT` | Port | `5432` |
| `LOG_LEVEL` | Application log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL` (case-insensitive) | `INFO` |

The same file is read by the PostgreSQL container: changing the password **after** the volume was created has no effect on an existing database (you then need `docker compose down -v`, which deletes the data).

### Checking the connection

`GET /health/db` runs `SELECT 1`: `200 {"status": "ok"}` if the database answers, otherwise `503 {"detail": "Base de données indisponible"}` (the detailed error is in the backend logs).

### Migrations (Alembic)

| Action | Command |
|---|---|
| Create a migration from the models | `uv run alembic revision --autogenerate -m "description"` |
| Apply migrations | `uv run alembic upgrade head` |
| Revert the last migration | `uv run alembic downgrade -1` |
| Show the database's current version | `uv run alembic current` |

Models must inherit from `app.db.base.Base` and be imported by `migrations/env.py` to be detected by `--autogenerate`. **Always review** a generated migration before applying it.

---

## 10. Logging

Application logs (loggers under `app`, e.g. `logging.getLogger(__name__)` in `app/...`) are configured by `app/core/logging.py`:

- written to stderr with the **same format as uvicorn**, plus the logger name: `ERROR:    app.main - Échec de la connexion à la base de données`;
- level set by `LOG_LEVEL` (in `.env` or the environment, default `INFO`); an invalid value stops the application at startup with a clear error;
- uvicorn's own logs keep their configuration: use `--log-level` on `fastapi dev` / `fastapi run` to change them.
