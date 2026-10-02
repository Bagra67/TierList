# Testing guide

English | [Français](testing.fr.md)

This guide explains how the TierList tests work: the tools used, what each test does, why it exists and what result is expected.

| | Backend | Frontend |
| --- | --- | --- |
| Test tool | [pytest](https://docs.pytest.org/) | [Vitest](https://vitest.dev/) |
| Helpers | FastAPI `TestClient`, pytest fixtures, pytest-cov | Testing Library, jsdom, jest-dom, v8 coverage |
| Where | `backend/tests/` | next to the code: `frontend/src/**/*.test.tsx` |
| Run | `uv run pytest` (in `backend/`) | `pnpm test` (in `frontend/`) |
| Coverage | `uv run pytest --cov=app` | `pnpm test:coverage` |

Both test suites also run on **every pull request** in the CI (`.github/workflows/ci.yml`). A PR cannot be merged into `develop` or `main` while a test fails.

---

## 1. Backend (pytest)

### 1.1 How pytest works

- **Discovery**: pytest looks in `tests/` (configured in `pyproject.toml`) for files named `test_*.py`, and runs every function named `test_*` inside them.
- **Assertions**: a test is a plain function that uses `assert`. If an `assert` fails or an exception is raised, the test **fails**, and pytest shows the values that were compared.
- **Fixtures**: reusable setup given to a test through its parameters. For example, `def test_x(client)` receives the `client` fixture. A fixture can run cleanup code after the test (the part after `yield`). Its *scope* says how often it is created: for each test (default) or once per run (`scope="session"`).
- **Built-in fixtures used here**:
  - `monkeypatch` changes environment variables or the current folder for one test only;
  - `tmp_path` provides an empty temporary folder;
  - `capsys` captures what is written to stdout/stderr.
- **Markers**: labels on tests. `integration` marks the tests that need a real PostgreSQL, so you can select them with `-m integration` or exclude them with `-m "not integration"`.
- **FastAPI `TestClient`**: sends HTTP requests to the application **in memory**, without starting a server. For example, `client.get("/hello")` returns a response whose `status_code` and `json()` can be checked.
- **`app.dependency_overrides`**: replaces a FastAPI dependency during a test. The tests replace `get_db_session`, the dependency that provides the database session, to simulate a working or broken database.

### 1.2 Running the tests

| Command (in `backend/`) | Effect |
| --- | --- |
| `uv run pytest` | All tests |
| `uv run pytest -v` | One line per test, with its name and result |
| `uv run pytest -m "not integration"` | Unit tests only (no database needed) |
| `uv run pytest -m integration` | Integration tests only (database needed) |
| `uv run pytest --cov=app` | All tests, plus a coverage table of `app/` |
| `uv run pytest tests/test_logging.py::test_log_level_defaults_to_info` | A single test |

Integration tests need PostgreSQL to be running: `docker compose up -d --wait` from the repository root.

### 1.3 Unit tests: `tests/test_main.py` (API endpoints)

These tests call the API with `TestClient`. They never need a real database.

| Test | What it does | Purpose | Expected result |
| --- | --- | --- | --- |
| `test_hello` | Calls `GET /hello`. | Checks the endpoint the frontend displays. | `200` and `{"message": "Hello World"}`. |
| `test_health_db_ok` | Replaces the database session with one on an **in-memory SQLite** database, then calls `GET /health/db`. | Checks the success path of the database health check without PostgreSQL. | `200` and `{"status": "ok"}`. |
| `test_health_db_unavailable` | Replaces the session with a fake object whose `execute` raises `OperationalError`, the error SQLAlchemy raises when the database is unreachable. | Checks that a database outage is turned into a clean API error, without internal details. | `503` and `{"detail": "Base de données indisponible"}`. |

The `clear_dependency_overrides` fixture runs automatically after each test (`autouse=True`) and removes the replacements, so that tests never affect each other.

### 1.4 Unit tests: `tests/test_logging.py` (logging)

| Test | What it does | Purpose | Expected result |
| --- | --- | --- | --- |
| `test_log_level_defaults_to_info` | Removes `LOG_LEVEL`, then reads the logging settings. | Checks the default level. | `log_level == "INFO"`. |
| `test_log_level_is_case_insensitive` | Sets `LOG_LEVEL=debug`. | Users may write the level in lowercase. | `log_level == "DEBUG"`. |
| `test_invalid_log_level_is_rejected` | Sets `LOG_LEVEL=LOUD`. | A typo must be detected instead of being silently ignored. | `ValidationError` is raised. |
| `test_app_logs_use_uvicorn_format_and_respect_level` | Sets the level to `WARNING`, writes an `info` and a `warning` log, and captures stderr with `capsys`. | Checks level filtering and the output format. | The `info` message is absent; the output contains `WARNING:` and `app.example - visible message`. |
| `test_database_failure_is_logged_with_traceback` | Simulates an unreachable database, calls `GET /health/db` and captures stderr. | A database outage must be visible in the server logs, with the error details, for troubleshooting. | `503`; stderr contains `ERROR:`, `app.main - Échec de la connexion à la base de données` and `OperationalError`. |

Two fixtures keep these tests independent:
- `no_env_file` moves the test into an empty temporary folder (`tmp_path`). Your local `.env` is therefore never read, and only the variables set by the test count.
- `restore_default_logging` runs after each test: it resets the logging configuration to `INFO` and removes the dependency replacements.

### 1.5 Integration tests: `tests/integration/` (real PostgreSQL)

These tests check what fakes cannot: the real connection, the real SQL and the Alembic migrations. They are marked `integration`.

The fixtures in `tests/integration/conftest.py` prepare the database in steps. Each step uses the previous one:

| Fixture | Scope | What it does |
| --- | --- | --- |
| `test_database_url` | once per run | Reads the PostgreSQL settings, connects to the server and creates the **`<POSTGRES_DB>_test`** database (e.g. `tierlist_test`) if it is missing. Development data is **never touched**. |
| `migrated_engine` | once per run | Applies the Alembic migrations (`upgrade head`) to the test database, then provides a connection engine. |
| `db_session` | each test | Opens a transaction and gives the test a session inside it. At the end of the test, the transaction is **rolled back**: nothing the test wrote remains, so each test starts from a clean database. |
| `client` | each test | A `TestClient` whose database dependency uses `db_session`. |

| Test | What it does | Purpose | Expected result |
| --- | --- | --- | --- |
| `test_health_db_against_real_postgres` | Calls `GET /health/db` with the real database session. | Checks the full chain: settings, SQLAlchemy, psycopg driver, PostgreSQL. | `200` and `{"status": "ok"}`. |

**When PostgreSQL is not available:**
- **Locally**, integration tests are **skipped**, with the message `PostgreSQL is not reachable: start it with docker compose up -d --wait`. The other tests still run.
- **On CI** (`CI=true`), they **fail** instead: a missing database there is a real problem that must not be hidden.

### 1.6 Contract test: `tests/test_openapi.py` (API contract)

| Test | What it does | Purpose | Expected result |
| --- | --- | --- | --- |
| `test_openapi_schema_is_up_to_date` | Builds the OpenAPI schema from the application (`render_openapi()` in `scripts/export_openapi.py`) and compares it with the committed `backend/openapi.json`. | The frontend generates its TypeScript types from this file: it must always match the real API. | Identical. Otherwise the test fails and tells you to run `uv run python scripts/export_openapi.py`, then `pnpm gen:api`. |

On the frontend side, the CI step **Check API types are up to date** regenerates `src/api/schema.d.ts` and fails if it differs from the committed file. A contract change that breaks the frontend makes `pnpm typecheck` fail, including in the test mocks.

---

## 2. Frontend (Vitest)

### 2.1 How Vitest works

- **Discovery**: Vitest runs every `*.test.ts` / `*.test.tsx` file. It is configured in the `test` block of `vite.config.ts`.
- **Structure**:
  - `describe('App', …)` groups related tests;
  - `it('…', …)` is one test;
  - `expect(value).toBe…()` is an assertion, and the test fails if it is not satisfied.
- **jsdom**: a browser simulated in Node.js. Components can be rendered and inspected without opening a real browser.
- **Testing Library**:
  - `render(<App />)` displays the component;
  - `screen` searches the page **the way a user sees it**: by visible text (`getByText`) or by accessibility role (`getByRole('heading')`, `findByRole('alert')`);
  - `getBy…` searches immediately, while `findBy…` **waits** for the element to appear, which is useful after an asynchronous call.
- **jest-dom**: adds readable assertions such as `toBeInTheDocument()` and `toHaveTextContent()`. It is loaded by `src/test/setup.ts`, which also unmounts components after each test.
- **Mocks** (`vi.fn`, `vi.stubGlobal`, `vi.spyOn`): replace a function with a fake whose behavior the test decides. Here, the global `fetch` is replaced by `vi.stubGlobal('fetch', …)` and restored by `vi.unstubAllGlobals()` after each test, so tests **never call the real backend**: they are fast and do not depend on a running server. Everything above `fetch` (API client, TanStack Query hooks, components) runs for real.
- **`renderWithQueryClient`** (`src/test/renderWithQueryClient.tsx`): renders a component inside a **new** TanStack Query client for each test, so no cached data leaks from one test to the next. Retries are disabled (`retry: false`) so error cases fail immediately. Use it instead of `render` for any component that loads data.

### 2.2 Running the tests

| Command (in `frontend/`) | Effect |
| --- | --- |
| `pnpm test` | Runs all tests once |
| `pnpm test:watch` | Re-runs the affected tests on every file change |
| `pnpm test:coverage` | All tests, plus a coverage table of `src/` |

### 2.3 Tests: `src/App.test.tsx`

`fetch` is stubbed by the `stubFetch` helper and `App` is rendered with `renderWithQueryClient`, so the whole chain `useHello` → `getHello` → `apiClient` runs.

| Test | What it does | Purpose | Expected result |
| --- | --- | --- | --- |
| `shows a loading message while the backend answers` | `fetch` returns a promise that never resolves, simulating a slow backend. | Checks the loading state. | The text `Chargement…` is displayed. |
| `shows the message returned by the backend` | `fetch` answers `200` with `{ message: 'Hello World' }`. | Checks the success state: the backend message is shown. | A heading (`<h1>`) with the text `Hello World` appears. |
| `shows an alert when the backend cannot be reached` | `fetch` answers `500`. `console.error` is silenced with `vi.spyOn` and checked. | Checks the error state: the user is told, and the error is logged for developers (by the query client in `src/api/queryClient.ts`). | An element with the `alert` role contains `Impossible de joindre le backend`, and `console.error` was called. |

### 2.4 Tests: `src/api/hello.test.ts`

Tests of `getHello`, the API call itself, with a stubbed `fetch`.

| Test | What it does | Purpose | Expected result |
| --- | --- | --- | --- |
| `calls GET /api/hello and returns the JSON body` | `fetch` answers `200` with `{ message: 'Hello World' }`; the test inspects the request sent. | Checks that the shared client targets the right URL (`/api` prefix, forwarded by the Vite proxy) and returns the typed body. | `{ message: 'Hello World' }` is returned; the request is a `GET` on `/api/hello`. |
| `throws an ApiError carrying the status when the backend fails` | `fetch` answers `500` with `{ detail: 'boom' }`. | Checks the error contract: every non-2xx response becomes an `ApiError` that callers can inspect. | An `ApiError` with `status: 500` and `body: { detail: 'boom' }` is thrown. |

---

## 3. Reading the results

| Result | Meaning |
| --- | --- |
| `passed` / ✓ | The test ran and every assertion was satisfied. |
| `failed` / ✗ | An assertion was not satisfied, or an unexpected error was raised. The output shows the expected and actual values. |
| `skipped` (backend) | The test was not run, with the reason in the output (`uv run pytest -rs` lists the reasons). Currently, this happens only for integration tests when PostgreSQL is not running locally. |
| `error` (backend) | A fixture failed before the test could run, e.g. no database on CI. |

**Coverage** shows, for each file, the share of code executed by the tests:
- backend (pytest-cov): `Stmts` (statements), `Miss` (statements no test executed) and `Cover` (percentage);
- frontend (Vitest): `% Stmts` (statements), `% Branch` (`if`/`else` paths), `% Funcs` (functions), `% Lines` (lines) and `Uncovered Line #s` (lines no test executed).

There is no minimum threshold for now. Coverage helps find untested code, but it does not prove the tests are good.

### 3.1 Test report on CI

Each CI run (GitHub → **Actions** → the run → **Summary**) shows, for the **Backend** and **Frontend** jobs:

| Section | Content |
| --- | --- |
| Header | Verdict (✅ Passed / ❌ Failed) and totals: tests, passed, failed, skipped, total duration. |
| ❌ Failures | Only if a test failed: its name, the error message and, in a collapsible block, the assertion details and traceback. |
| ⏭️ Skipped | Only if tests were skipped: each test with the reason. |
| All tests | One line per test: status, name (`file::test` or `file › describe > test`) and duration. |
| 🐢 Slowest tests | The 5 slowest tests, to spot tests that are getting slow. Shown when there are more than 5 tests. |
| Coverage | Coverage table (backend per file, frontend per metric). |

The report is also produced **when tests fail**, so the cause can be read without opening the logs. It is generated from the JUnit XML reports of pytest (`--junitxml`) and Vitest (`junit` reporter) by `.github/scripts/junit_summary.py`, which only uses the Python standard library.

The raw reports (JUnit XML and coverage) are attached to the run as **artifacts** (`backend-test-reports`, `frontend-test-reports`) for 14 days.

---

## 4. Writing a new test

1. **Test the behavior, not the implementation**:
   - backend: check the HTTP status and JSON body;
   - frontend: check what the user sees, using text and roles.
2. **One test, one behavior**, with a name that says what is expected, e.g. `test_invalid_log_level_is_rejected`.
3. **Cover the error cases and the edge cases**, not only the success path.
4. **Keep tests independent**: use fixtures and `dependency_overrides`, and clean up after the test (`autouse` fixtures, `vi.unstubAllGlobals`, `mockRestore`).
5. **Choose the right level**:
   - a unit test with fakes for the logic and the API contract;
   - an integration test (`tests/integration/`, `integration` marker) as soon as real SQL or migrations are involved.
6. Put new frontend tests next to the component (`Component.test.tsx`) and new backend tests in `backend/tests/`.
7. Run the tests locally before pushing; CI runs them again on the PR.
8. **Update this guide in the same PR**, in both languages (`testing.md` and `testing.fr.md`), whenever a test, a fixture or a test tool is added, changed or removed (AGENTS.md §28).
