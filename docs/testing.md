# Testing guide

English | [Français](testing.fr.md)

This guide explains how the TierList tests work: the tools used, what each test does, why it exists and what result is expected.

|           | Backend                                           | Frontend                                       |
| --------- | ------------------------------------------------- | ---------------------------------------------- |
| Test tool | [pytest](https://docs.pytest.org/)                | [Vitest](https://vitest.dev/)                  |
| Helpers   | FastAPI `TestClient`, pytest fixtures, pytest-cov | Testing Library, jsdom, jest-dom, v8 coverage  |
| Where     | `backend/tests/`                                  | next to the code: `frontend/src/**/*.test.tsx` |
| Run       | `uv run pytest` (in `backend/`)                   | `pnpm test` (in `frontend/`)                   |
| Coverage  | `uv run pytest --cov=app`                         | `pnpm test:coverage`                           |

Both test suites also run on **every pull request** in the CI (`.github/workflows/ci.yml`). A PR cannot be merged into `develop` or `main` while a test fails.

---

## 1. Backend (pytest)

### 1.1 How pytest works

- **Discovery**: pytest looks in `tests/` (configured in `pyproject.toml`) for files named `test_*.py`, and runs every function named `test_*` inside them.
- **Assertions**: a test is a plain function that uses `assert`. If an `assert` fails or an exception is raised, the test **fails**, and pytest shows the values that were compared.
- **Fixtures**: reusable setup given to a test through its parameters. For example, `def test_x(client)` receives the `client` fixture. A fixture can run cleanup code after the test (the part after `yield`). Its _scope_ says how often it is created: for each test (default) or once per run (`scope="session"`).
- **Built-in fixtures used here**:
  - `monkeypatch` changes environment variables or the current folder for one test only;
  - `tmp_path` provides an empty temporary folder;
  - `capsys` captures what is written to stdout/stderr.
- **Markers**: labels on tests. `integration` marks the tests that need a real PostgreSQL, so you can select them with `-m integration` or exclude them with `-m "not integration"`.
- **FastAPI `TestClient`**: sends HTTP requests to the application **in memory**, without starting a server. For example, `client.get("/hello")` returns a response whose `status_code` and `json()` can be checked.
- **`app.dependency_overrides`**: replaces a FastAPI dependency during a test. The tests replace `get_db_session`, the dependency that provides the database session, to simulate a working or broken database.

### 1.2 Running the tests

| Command (in `backend/`)                                                | Effect                                      |
| ---------------------------------------------------------------------- | ------------------------------------------- |
| `uv run pytest`                                                        | All tests                                   |
| `uv run pytest -v`                                                     | One line per test, with its name and result |
| `uv run pytest -m "not integration"`                                   | Unit tests only (no database needed)        |
| `uv run pytest -m integration`                                         | Integration tests only (database needed)    |
| `uv run pytest --cov=app`                                              | All tests, plus a coverage table of `app/`  |
| `uv run pytest tests/test_logging.py::test_log_level_defaults_to_info` | A single test                               |

Integration tests need PostgreSQL to be running: `docker compose up -d --wait` from the repository root.

### 1.3 Unit tests: `tests/test_main.py` (API endpoints)

These tests call the API with `TestClient`. They never need a real database.

| Test                         | What it does                                                                                                                                     | Purpose                                                                                   | Expected result                                         |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| `test_hello`                 | Calls `GET /hello`.                                                                                                                              | Checks the endpoint the frontend displays.                                                | `200` and `{"message": "Hello World"}`.                 |
| `test_health`                | Calls `GET /health` without replacing any dependency.                                                                                            | The liveness probe must answer without the database.                                      | `200` and `{"status": "ok"}`.                           |
| `test_health_db_ok`          | Replaces the database session with one on an **in-memory SQLite** database, then calls `GET /health/db`.                                         | Checks the success path of the database health check without PostgreSQL.                  | `200` and `{"status": "ok"}`.                           |
| `test_health_db_unavailable` | Replaces the session with a fake object whose `execute` raises `OperationalError`, the error SQLAlchemy raises when the database is unreachable. | Checks that a database outage is turned into a clean API error, without internal details. | `503` and `{"detail": "Base de données indisponible"}`. |

The `clear_dependency_overrides` fixture runs automatically after each test (`autouse=True`) and removes the replacements, so that tests never affect each other.

### 1.4 Unit tests: `tests/test_logging.py` (logging)

| Test                                                 | What it does                                                                                          | Purpose                                                                                            | Expected result                                                                                                  |
| ---------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `test_log_level_defaults_to_info`                    | Removes `LOG_LEVEL`, then reads the logging settings.                                                 | Checks the default level.                                                                          | `log_level == "INFO"`.                                                                                           |
| `test_log_level_is_case_insensitive`                 | Sets `LOG_LEVEL=debug`.                                                                               | Users may write the level in lowercase.                                                            | `log_level == "DEBUG"`.                                                                                          |
| `test_invalid_log_level_is_rejected`                 | Sets `LOG_LEVEL=LOUD`.                                                                                | A typo must be detected instead of being silently ignored.                                         | `ValidationError` is raised.                                                                                     |
| `test_app_logs_use_uvicorn_format_and_respect_level` | Sets the level to `WARNING`, writes an `info` and a `warning` log, and captures stderr with `capsys`. | Checks level filtering and the output format.                                                      | The `info` message is absent; the output contains `WARNING:` and `app.example - visible message`.                |
| `test_database_failure_is_logged_with_traceback`     | Simulates an unreachable database, calls `GET /health/db` and captures stderr.                        | A database outage must be visible in the server logs, with the error details, for troubleshooting. | `503`; stderr contains `ERROR:`, `app.main - Échec de la connexion à la base de données` and `OperationalError`. |

Two fixtures keep these tests independent:

- `no_env_file` moves the test into an empty temporary folder (`tmp_path`). Your local `.env` is therefore never read, and only the variables set by the test count.
- `restore_default_logging` runs after each test: it resets the logging configuration to `INFO` and removes the dependency replacements.

### 1.5 Integration tests: `tests/integration/` (real PostgreSQL)

These tests check what fakes cannot: the real connection, the real SQL and the Alembic migrations. They are marked `integration`.

The fixtures in `tests/integration/conftest.py` prepare the database in steps. Each step uses the previous one:

| Fixture             | Scope        | What it does                                                                                                                                                                                       |
| ------------------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test_database_url` | once per run | Reads the PostgreSQL settings, connects to the server and creates the **`<POSTGRES_DB>_test`** database (e.g. `tierlist_test`) if it is missing. Development data is **never touched**.            |
| `migrated_engine`   | once per run | Applies the Alembic migrations (`upgrade head`) to the test database, then provides a connection engine.                                                                                           |
| `db_session`        | each test    | Opens a transaction and gives the test a session inside it. At the end of the test, the transaction is **rolled back**: nothing the test wrote remains, so each test starts from a clean database. |
| `client`            | each test    | A `TestClient` whose database dependency uses `db_session`.                                                                                                                                        |

| Test                                   | What it does                                           | Purpose                                                                  | Expected result               |
| -------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------ | ----------------------------- |
| `test_health_db_against_real_postgres` | Calls `GET /health/db` with the real database session. | Checks the full chain: settings, SQLAlchemy, psycopg driver, PostgreSQL. | `200` and `{"status": "ok"}`. |

#### `tests/integration/test_auth.py` (authentication)

These tests go through the real routes, service, repositories and migrations. The `auth_client` fixture wraps `client` and replaces the settings (`get_settings`) so that the refresh cookie is not `Secure` and uses the path `/auth`: `TestClient` talks plain HTTP to `http://testserver/auth/...`, without the `/api` proxy, and would otherwise never send the cookie back. Shared helpers: `register` (creates Alice and returns her access token) and `bearer` (the `Authorization` header).

| Test                                                              | What it does                                                                                                                     | Purpose                                                      | Expected result                                                                                                                                                            |
| ----------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test_register_creates_the_account_and_returns_tokens`            | Registers `Alice@Example.com`, then reads the `users` and `refresh_tokens` tables.                                               | Checks the success path and what is stored.                  | `201`, `token_type` `bearer`, `expires_in` `900`, a `refresh_token` cookie; email stored in lowercase, password hashed, only the SHA-256 hash of the refresh token stored. |
| `test_register_rejects_an_email_already_used_whatever_its_case`   | Registers twice, the second time with `ALICE@example.COM`.                                                                       | Emails are unique regardless of case.                        | `409` and `{"detail": "Cet email est déjà utilisé"}`.                                                                                                                      |
| `test_register_validates_its_input` (3 cases)                     | Sends an invalid email, a password shorter than 8 characters, or a blank display name.                                           | Each field is validated by the API.                          | `422`, with only the faulty field (`body.<field>`) in `errors`.                                                                                                            |
| `test_me_returns_the_authenticated_user`                          | Calls `GET /auth/me` with the access token from registration.                                                                    | Checks the Bearer authentication.                            | `200`, email and display name; no `password_hash` in the body.                                                                                                             |
| `test_me_requires_a_valid_access_token` (2 cases)                 | Calls `GET /auth/me` without a token, then with `not-a-jwt`.                                                                     | A protected route refuses anonymous calls.                   | `401`, `{"detail": "Authentification requise"}` and `WWW-Authenticate: Bearer`.                                                                                            |
| `test_login_with_valid_credentials`                               | Registers, clears the cookies, then signs in with the email in another case.                                                     | Checks sign-in.                                              | `200`, new `refresh_token` cookie, and the access token opens `GET /auth/me`.                                                                                              |
| `test_login_failures_are_indistinguishable` (2 cases)             | Signs in with a wrong password, then with an unknown email.                                                                      | The answer must not reveal which emails have an account.     | `401` and the same `{"detail": "Email ou mot de passe incorrect"}` in both cases.                                                                                          |
| `test_refresh_rotates_the_refresh_token`                          | Calls `POST /auth/refresh` with the registration cookie.                                                                         | Checks the rotation.                                         | `200`, a different `refresh_token` cookie, and the new access token works.                                                                                                 |
| `test_replaying_a_rotated_refresh_token_revokes_the_whole_family` | Refreshes once, then presents the first (already replaced) token again, then the latest one.                                     | Theft detection: a replayed token revokes the whole session. | The replay gets `401` with `Session expirée, veuillez vous reconnecter`, and the latest token is refused too (`401`).                                                      |
| `test_expired_refresh_token_is_rejected`                          | Moves the stored token's `expires_at` into the past, then refreshes.                                                             | An expired token cannot be used.                             | `401`.                                                                                                                                                                     |
| `test_unknown_refresh_token_is_rejected_and_clears_the_cookie`    | Refreshes with a cookie that matches no token.                                                                                   | The browser must not keep a useless cookie.                  | `401`, and `Set-Cookie` empties the cookie (`Max-Age=0`).                                                                                                                  |
| `test_refresh_without_cookie_is_rejected`                         | Refreshes without any cookie.                                                                                                    | No session without a cookie.                                 | `401`.                                                                                                                                                                     |
| `test_logout_revokes_the_session`                                 | Signs out, then tries to refresh with the old cookie.                                                                            | Sign-out closes the session on the server.                   | `204`, cookie removed, then `401` on refresh.                                                                                                                              |
| `test_logout_without_session_succeeds`                            | Signs out without a cookie.                                                                                                      | Signing out never fails.                                     | `204`.                                                                                                                                                                     |
| `test_refresh_cookie_attributes`                                  | Registers with the production cookie settings and reads `Set-Cookie`.                                                            | Checks the cookie protections.                               | `HttpOnly`, `Secure`, `SameSite=strict`, `Path=/api/auth` and `Max-Age=2592000` (30 days).                                                                                 |
| `test_delete_account_removes_the_user_and_its_sessions`           | Registers, then calls `DELETE /auth/me` with the password; reads the tables, then tries `GET /auth/me`, a refresh and a sign-in. | Deletion is permanent and ends every session.                | `204`, cookie removed, `users` and `refresh_tokens` empty; then `401` for `GET /auth/me`, the refresh and the sign-in.                                                     |
| `test_delete_account_requires_the_right_password`                 | Deletes with a wrong password.                                                                                                   | A stolen access token alone cannot delete the account.       | `403`, `{"detail": "Mot de passe incorrect"}`; the user still exists.                                                                                                      |
| `test_delete_account_requires_an_access_token`                    | Deletes without the `Authorization` header.                                                                                      | Only an authenticated user can delete their account.         | `401`.                                                                                                                                                                     |
| `test_delete_account_requires_a_password`                         | Deletes with an empty body.                                                                                                      | The password is mandatory.                                   | `422`, with `body.password` in `errors`.                                                                                                                                   |

**When PostgreSQL is not available:**

- **Locally**, integration tests are **skipped**, with the message `PostgreSQL is not reachable: start it with docker compose up -d --wait`. The other tests still run.
- **On CI** (`CI=true`), they **fail** instead: a missing database there is a real problem that must not be hidden.

### 1.6 Contract test: `tests/test_openapi.py` (API contract)

| Test                                | What it does                                                                                                                                                  | Purpose                                                                                        | Expected result                                                                                                          |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `test_openapi_schema_is_up_to_date` | Builds the OpenAPI schema from the application (`render_openapi()` in `scripts/export_openapi.py`) and compares it with the committed `backend/openapi.json`. | The frontend generates its TypeScript types from this file: it must always match the real API. | Identical. Otherwise the test fails and tells you to run `uv run python scripts/export_openapi.py`, then `pnpm gen:api`. |

On the frontend side, the CI step **Check API types are up to date** regenerates `src/api/schema.d.ts` and fails if it differs from the committed file. A contract change that breaks the frontend makes `pnpm typecheck` fail, including in the test mocks.

### 1.7 Unit tests: `tests/test_errors.py` (error format)

These tests use a small dedicated FastAPI application with `register_error_handlers` and three test routes: adding them to `app.main` would change the API contract. Its `TestClient` is created with `raise_server_exceptions=False` so that an exception becomes a response, as on a real server.

| Test                                              | What it does                                                                            | Purpose                                                                                                   | Expected result                                                                                                                                                    |
| ------------------------------------------------- | --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `test_unexpected_error_returns_generic_500`       | Calls a route that raises `RuntimeError("secret internal detail")` and captures stderr. | An unexpected error must not leak internal details to the client, but must be logged for troubleshooting. | `500` with `{"detail": "Erreur interne du serveur"}`, without the exception message; stderr contains `ERROR:`, `Erreur non gérée sur GET /boom` and the exception. |
| `test_validation_error_lists_invalid_fields`      | Calls `/items/abc` (non-integer `item_id`, missing `limit`).                            | Checks the 422 format the frontend relies on.                                                             | `422`, `detail` is `Requête invalide`, `errors` lists `path.item_id` and `query.limit`, each with a message.                                                       |
| `test_http_exception_keeps_its_status_and_detail` | Calls a route that raises `HTTPException(404, "Introuvable")`.                          | Expected errors keep their status and message.                                                            | `404` with `{"detail": "Introuvable"}`.                                                                                                                            |

### 1.8 Unit test: `tests/test_versions.py` (version)

| Test                        | What it does                                                                                                    | Purpose                                                                                                | Expected result             |
| --------------------------- | --------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | --------------------------- |
| `test_versions_are_in_sync` | Reads the version of `backend/pyproject.toml` and `frontend/package.json` and compares them with `app.version`. | The repository has a single version ([releasing guide](releasing.md)); the `Release` workflow tags it. | The three values are equal. |

### 1.9 Unit tests: `tests/test_security.py` (authentication primitives)

Tests of the pure functions of `app/core/security.py`, with a test signing key: no database, no settings.

| Test                                                          | What it does                                                                                                                  | Purpose                                                       | Expected result                                                                |
| ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `test_password_hash_verifies_only_the_original_password`      | Hashes a password, then verifies it and a wrong one.                                                                          | Checks the Argon2id hashing.                                  | The hash differs from the password; only the original password is accepted.    |
| `test_access_token_round_trip`                                | Creates an access token, then decodes it.                                                                                     | Checks the claims.                                            | Same user id and same `auth_time`.                                             |
| `test_expired_access_token_is_rejected`                       | Creates a token issued one hour ago, valid 15 minutes.                                                                        | An expired token is refused.                                  | `InvalidAccessTokenError`.                                                     |
| `test_access_token_signed_with_another_key_is_rejected`       | Signs with another key.                                                                                                       | A forged token is refused.                                    | `InvalidAccessTokenError`.                                                     |
| `test_invalid_access_tokens_are_rejected` (4 cases)           | Decodes a token of type `refresh`, a token whose `sub` is not a UUID, a token without expiry, and a string that is not a JWT. | Any malformed token is refused.                               | `InvalidAccessTokenError` each time.                                           |
| `test_unsigned_access_token_is_rejected`                      | Decodes an unsigned `alg: none` token.                                                                                        | Classic attack on JWT libraries.                              | `InvalidAccessTokenError`.                                                     |
| `test_refresh_tokens_are_random_and_hashed_deterministically` | Generates two refresh tokens and hashes them.                                                                                 | The stored hash must be reproducible to find the token again. | Two different tokens; same hash for the same token; 64 hexadecimal characters. |

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
- **`<dialog>` in jsdom**: jsdom handles the `open` attribute of `<dialog>` but not `showModal()` and `close()`; `src/test/setup.ts` adds a minimal version of both (`close()` also fires the `close` event). The focus trap and the Escape key, handled by the browser, cannot be tested here.
- **`stubBackend`** (`src/test/stubBackend.ts`): replaces `fetch` with a fake backend described route by route (`'GET /auth/me': () => Response.json(alice)`); an undeclared route answers `404`, so an unexpected call makes the test fail. `calledRoutes` lists the calls received, and `alice`, `tokenResponse` and `unauthorized` are ready-made answers. Tests that use the API client also call `setAccessToken(null)` after each test, since the access token is kept in memory by `src/api/client.ts`.

### 2.2 Running the tests

| Command (in `frontend/`) | Effect                                          |
| ------------------------ | ----------------------------------------------- |
| `pnpm test`              | Runs all tests once                             |
| `pnpm test:watch`        | Re-runs the affected tests on every file change |
| `pnpm test:coverage`     | All tests, plus a coverage table of `src/`      |

### 2.3 Tests: `src/App.test.tsx`

`App` (the routes) is rendered inside a `MemoryRouter` at a given path, with `renderWithQueryClient` and `stubBackend`: router, guard, hooks and API client all run.

| Test                                                | What it does                                        | Purpose                                               | Expected result                                             |
| --------------------------------------------------- | --------------------------------------------------- | ----------------------------------------------------- | ----------------------------------------------------------- |
| `redirects to the login page without a session`     | Opens `/`; `POST /auth/refresh` answers `401`.      | Private pages require a session.                      | The `Connexion` heading is shown.                           |
| `restores the session and shows the home page`      | Opens `/`; refresh and `GET /auth/me` succeed.      | A valid refresh cookie restores the session at load.  | The `Hello World` heading and `Connecté en tant que Alice`. |
| `shows an alert when the backend cannot be reached` | Refresh answers `502`. `console.error` is silenced. | A backend outage is not mistaken for "not signed in". | An `alert` containing `Impossible de joindre le backend`.   |
| `logs out and goes back to the login page`          | Clicks `Se déconnecter`.                            | Checks sign-out.                                      | The `Connexion` heading is shown.                           |
| `redirects unknown pages to the home page`          | Opens `/does-not-exist` with a session.             | Unknown paths do not show a blank page.               | The `Hello World` heading.                                  |

### 2.4 Tests: `src/api/hello.test.ts`

Tests of `getHello`, the API call itself, with a stubbed `fetch`.

| Test                                                                  | What it does                                                                                   | Purpose                                                                                                                      | Expected result                                                                               |
| --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `calls GET /api/hello and returns the JSON body`                      | `fetch` answers `200` with `{ message: 'Hello World' }`; the test inspects the request sent.   | Checks that the shared client targets the right URL (`/api` prefix, forwarded by the Vite proxy) and returns the typed body. | `{ message: 'Hello World' }` is returned; the request is a `GET` on `/api/hello`.             |
| `throws an ApiError carrying the status when the backend fails`       | `fetch` answers `500` with `{ detail: 'boom' }` (the backend's `ErrorResponse` format).        | Checks the error contract: every non-2xx response becomes an `ApiError` that callers can inspect.                            | An `ApiError` with `status: 500`, `body: { detail: 'boom' }` and `message: 'boom'` is thrown. |
| `falls back to the HTTP status when the body is not an ErrorResponse` | `fetch` answers `502` with a plain-text body, as the Vite proxy does when the backend is down. | The error stays usable even when the body does not come from the backend.                                                    | An `ApiError` with `status: 502` and `message: 'HTTP 502'` is thrown.                         |

### 2.5 Tests: `src/pages/HomePage.test.tsx`

The home page with a restored session; only `GET /hello` changes between tests.

| Test                                                               | What it does                                                         | Purpose                                                        | Expected result                                                                           |
| ------------------------------------------------------------------ | -------------------------------------------------------------------- | -------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `shows a loading message while the backend answers`                | `GET /hello` never answers.                                          | Checks the loading state.                                      | `Chargement…` is shown.                                                                   |
| `shows the message returned by the backend and the connected user` | `GET /hello` answers `{ message: 'Hello World' }`.                   | Checks the success state.                                      | The `Hello World` heading and `Connecté en tant que Alice`.                               |
| `shows an alert when the backend cannot be reached`                | `GET /hello` answers `500`; `console.error` is silenced and checked. | The user is told, and the error is logged by the query client. | An `alert` containing `Impossible de joindre le backend`, and `console.error` was called. |

### 2.6 Tests: `src/pages/LoginPage.test.tsx` and `src/pages/RegisterPage.test.tsx`

The form is filled with `fireEvent.change` and sent with `fireEvent.click`; a `/` route shows `Accueil` to check the redirection.

| Test                                                                 | What it does                                            | Purpose                                      | Expected result                                                             |
| -------------------------------------------------------------------- | ------------------------------------------------------- | -------------------------------------------- | --------------------------------------------------------------------------- |
| Login: `sends the credentials and opens the home page`               | Valid credentials.                                      | Checks the request body and the redirection. | The `Accueil` heading; the request body is `{ email, password }`.           |
| Login: `shows the backend message when the credentials are wrong`    | `POST /auth/login` answers `401`.                       | The user understands why sign-in failed.     | An `alert` with `Email ou mot de passe incorrect`; still on the login page. |
| Login: `disables the button while the request is pending`            | `POST /auth/login` never answers.                       | Prevents double submissions.                 | A disabled `Connexion…` button.                                             |
| Login: `shows validation errors next to the field`                   | `POST /auth/login` answers `422` on `body.email`.       | 422 errors are shown on the right field.     | The message is shown and the email field has `aria-invalid="true"`.         |
| Register: `creates the account and opens the home page`              | Valid form.                                             | Checks the request body and the redirection. | The `Accueil` heading; the body is `{ email, password, display_name }`.     |
| Register: `shows the backend message when the email is already used` | `POST /auth/register` answers `409`.                    | Checks the duplicate email message.          | An `alert` with `Cet email est déjà utilisé`.                               |
| Register: `shows validation errors next to the field`                | `POST /auth/register` answers `422` on `body.password`. | 422 errors are shown on the right field.     | The message is shown.                                                       |

### 2.7 Tests: `src/api/client.test.ts` (authentication middleware)

| Test                                                               | What it does                                               | Purpose                                                                    | Expected result                                                                             |
| ------------------------------------------------------------------ | ---------------------------------------------------------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `sends the access token in the Authorization header`               | `GET /auth/me` only accepts `Bearer token-1`.              | Checks that the token in memory is sent.                                   | The user is returned.                                                                       |
| `refreshes an expired access token once, then retries the request` | The token in memory is refused; refresh returns a new one. | An expired token is renewed without the user noticing.                     | Calls in order: `GET /auth/me`, `POST /auth/refresh`, `GET /auth/me`; the user is returned. |
| `shares a single refresh between concurrent requests`              | Two requests with an expired token at the same time.       | Two refreshes with the same cookie would look like a theft to the backend. | A single `POST /auth/refresh`.                                                              |
| `returns the 401 when the session cannot be refreshed`             | Both `GET /auth/me` and refresh answer `401`.              | No infinite loop; the caller sees the 401.                                 | An `ApiError` with `status: 401`.                                                           |
| `never refreshes on a 401 from a session route such as login`      | `POST /auth/login` answers `401`.                          | A wrong password must not trigger a refresh.                               | Only `POST /auth/login` is called; its message is thrown.                                   |
| `getFieldErrors` › `maps validation errors to body field names`    | A 422 `ApiError` on `body.email`.                          | Forms show errors per field.                                               | `{ email: '<message>' }`.                                                                   |
| `getFieldErrors` › `returns no field error for other errors`       | A 500 `ApiError`, then `null`.                             | No false field errors.                                                     | `{}` both times.                                                                            |

### 2.8 Tests: `src/api/auth.test.ts`

| Test                                                                             | What it does                                                           | Purpose                                                    | Expected result                                                                                            |
| -------------------------------------------------------------------------------- | ---------------------------------------------------------------------- | ---------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `restores the session from the refresh cookie when no access token is in memory` | Refresh and `GET /auth/me` succeed.                                    | Checks the session restoration at page load.               | The user; calls: refresh then `GET /auth/me`.                                                              |
| `returns no user when there is no valid session`                                 | Refresh answers `401`.                                                 | "Not signed in" is a normal state, not an error.           | `null`, without calling `GET /auth/me`.                                                                    |
| `reports an unreachable backend instead of an anonymous user`                    | Refresh answers `502`.                                                 | A backend outage must not send the user to the login page. | An `ApiError` with `status: 502`.                                                                          |
| `keeps the access token returned by login for the next requests`                 | Signs in, then calls `GET /auth/me`, which only accepts the new token. | The token from sign-in is used afterwards.                 | The user is returned.                                                                                      |
| `forgets the access token on logout, even if the backend fails`                  | `POST /auth/logout` answers `500`.                                     | Signing out locally must always work.                      | An `ApiError` is thrown, and the logout request carries no `Authorization` header.                         |
| `forgets the access token once the account is deleted`                           | `DELETE /auth/me` answers `204`, then the session is read again.       | After deletion, no request may use the old token.          | `getCurrentUser()` returns `null`; calls: `DELETE /auth/me` then `POST /auth/refresh` (no `GET /auth/me`). |

### 2.9 Tests: `src/components/DeleteAccountDialog.test.tsx`

The dialog is rendered with a `/login` route that shows `Connexion`, to check the redirection.

| Test                                                                  | What it does                                                  | Purpose                                            | Expected result                                                                                                                                       |
| --------------------------------------------------------------------- | ------------------------------------------------------------- | -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `keeps the confirmation dialog closed until asked`                    | Renders, then clicks `Supprimer mon compte`.                  | Nothing is deleted by mistake: confirmation first. | No dialog at first; then a visible dialog named `Supprimer mon compte`.                                                                               |
| `deletes the account with the password, then opens the login page`    | Confirms with a password; `DELETE /auth/me` answers `204`.    | Checks the request and the redirection.            | The `Connexion` heading; a single `DELETE /auth/me` call, with body `{ password }`.                                                                   |
| `shows the backend message and stays open when the password is wrong` | `DELETE /auth/me` answers `403`.                              | The user can try again.                            | An `alert` with `Mot de passe incorrect`; the dialog is still visible.                                                                                |
| `closes on cancel and forgets the previous error`                     | After a `403`, clicks `Annuler`, then opens the dialog again. | Reopening starts from a clean form.                | The dialog closes; once reopened, no alert (awaited with `waitFor`, as TanStack Query notifies the reset asynchronously) and an empty password field. |

---

## 3. Reading the results

| Result              | Meaning                                                                                                                                                                                 |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `passed` / ✓        | The test ran and every assertion was satisfied.                                                                                                                                         |
| `failed` / ✗        | An assertion was not satisfied, or an unexpected error was raised. The output shows the expected and actual values.                                                                     |
| `skipped` (backend) | The test was not run, with the reason in the output (`uv run pytest -rs` lists the reasons). Currently, this happens only for integration tests when PostgreSQL is not running locally. |
| `error` (backend)   | A fixture failed before the test could run, e.g. no database on CI.                                                                                                                     |

**Coverage** shows, for each file, the share of code executed by the tests:

- backend (pytest-cov): `Stmts` (statements), `Miss` (statements no test executed) and `Cover` (percentage);
- frontend (Vitest): `% Stmts` (statements), `% Branch` (`if`/`else` paths), `% Funcs` (functions), `% Lines` (lines) and `Uncovered Line #s` (lines no test executed).

There is no minimum threshold for now. Coverage helps find untested code, but it does not prove the tests are good.

### 3.1 Test report on CI

Each CI run (GitHub → **Actions** → the run → **Summary**) shows, for the **Backend** and **Frontend** jobs:

| Section          | Content                                                                                                              |
| ---------------- | -------------------------------------------------------------------------------------------------------------------- |
| Header           | Verdict (✅ Passed / ❌ Failed) and totals: tests, passed, failed, skipped, total duration.                          |
| ❌ Failures      | Only if a test failed: its name, the error message and, in a collapsible block, the assertion details and traceback. |
| ⏭️ Skipped       | Only if tests were skipped: each test with the reason.                                                               |
| All tests        | One line per test: status, name (`file::test` or `file › describe > test`) and duration.                             |
| 🐢 Slowest tests | The 5 slowest tests, to spot tests that are getting slow. Shown when there are more than 5 tests.                    |
| Coverage         | Coverage table (backend per file, frontend per metric).                                                              |

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
