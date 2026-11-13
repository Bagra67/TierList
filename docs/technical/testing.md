# Testing guide

This guide explains how the TierList tests work: the tools, the shared setup, how to run them and how to write a new one. It does not list the tests: their names say what they check (see [Finding a test](#finding-a-test)).

|           | Backend                                           | Frontend                                       |
| --------- | ------------------------------------------------- | ---------------------------------------------- |
| Test tool | [pytest](https://docs.pytest.org/)                | [Vitest](https://vitest.dev/)                  |
| Helpers   | FastAPI `TestClient`, pytest fixtures, pytest-cov | Testing Library, jsdom, jest-dom, v8 coverage  |
| Where     | `backend/tests/`                                  | next to the code: `frontend/src/**/*.test.tsx` |
| Run       | `uv run pytest` (in `backend/`)                   | `pnpm test` (in `frontend/`)                   |
| Coverage  | `uv run pytest --cov=app`                         | `pnpm test:coverage`                           |

Both test suites also run on **every pull request** in the CI (`.github/workflows/ci.yml`). A PR cannot be merged into `develop` or `main` while a test fails.

A few critical journeys are also tested **end to end**, in real browsers against the real app: see [§6](#6-end-to-end-tests-playwright).

## Finding a test

Each test name is a sentence that says the expected behavior, e.g. `test_expired_access_token_is_rejected`. The test files are named after what they test (`tests/integration/test_room_guests.py`, `src/pages/RoomPage.test.tsx`). To list the tests:

| Suite                       | Command                                             |
| --------------------------- | --------------------------------------------------- |
| Backend (in `backend/`)     | `uv run pytest --collect-only -q`                   |
| Frontend (in `frontend/`)   | `pnpm vitest list`                                  |
| End to end (in `frontend/`) | `pnpm exec playwright test --list`                  |
| CI scripts (from the root)  | `python -m unittest discover -s .github/scripts -v` |

The CI test report also lists every test of a run, with its result and duration ([§3.1](#31-test-report-on-ci)).

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
- **Markers**: labels on tests. `integration` marks the tests that need a real PostgreSQL (or the S3 image storage), so you can select them with `-m integration` or exclude them with `-m "not integration"`.
- **FastAPI `TestClient`**: sends HTTP requests to the application **in memory**, without starting a server. For example, `client.get("/health")` returns a response whose `status_code` and `json()` can be checked.
- **`app.dependency_overrides`**: replaces a FastAPI dependency during a test. The tests replace `get_db_session`, the dependency that provides the database session, to simulate a working or broken database.

### 1.2 Running the tests

| Command (in `backend/`)                                                | Effect                                                                             |
| ---------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `uv run pytest`                                                        | All tests                                                                          |
| `uv run pytest -v`                                                     | One line per test, with its name and result                                        |
| `uv run pytest -m "not integration"`                                   | Unit tests only (no database needed)                                               |
| `uv run pytest -m integration`                                         | Integration tests only (database needed)                                           |
| `uv run pytest --cov=app`                                              | All tests, plus a coverage table of `app/`                                         |
| `uv run pytest -n auto`                                                | All tests in parallel (pytest-xdist), one process per CPU; the CI runs it this way |
| `uv run pytest tests/test_logging.py::test_log_level_defaults_to_info` | A single test                                                                      |

Integration tests need PostgreSQL, and SeaweedFS for the image storage tests, to be running: `docker compose up -d --wait` from the repository root.

### 1.3 Integration tests: `tests/integration/` (real PostgreSQL and S3)

These tests check what fakes cannot: the real connection, the real SQL, the Alembic migrations and the S3 image storage. They are marked `integration`.

The fixtures in `tests/integration/conftest.py` prepare the database in steps. Each step uses the previous one:

| Fixture                   | Scope        | What it does                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `test_database_url`       | once per run | Reads the PostgreSQL settings, connects to the server and creates the **`<POSTGRES_DB>_test`** database (e.g. `tierlist_test`) if it is missing. Development data is **never touched**.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `migrations_database_url` | once per run | Creates the **`<POSTGRES_DB>_test_migrations`** database if it is missing. It is reserved for the tests that downgrade the migrations, so the shared test database keeps its schema during the whole run.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `migrated_engine`         | once per run | Applies the Alembic migrations (`upgrade head`) to the test database, then provides a connection engine. `alembic_config(url)` (`tests/integration/helpers.py`) builds the Alembic configuration for a given database.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `db_session`              | each test    | Opens a transaction and gives the test a session inside it. At the end of the test, the transaction is **rolled back**: nothing the test wrote remains, so each test starts from a clean database.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `client`                  | each test    | A `TestClient` whose database dependency uses `db_session`, whose email sender is a fake (`FakeEmailSender`) that keeps the emails in `sent_emails`, and whose image storage is a fake (`FakeImageStorage`) that keeps the images in `stored_images`: no API test contacts an SMTP server or the S3 storage. Its session factory (`get_short_lived_session_factory`) gives the test session to the real-time channel, without closing it. It is the root application, like uvicorn: `TestClient(app, base_url="http://testserver/api")`, so the tests write API paths (`/auth/login`) sent to `/api/auth/login`, and `with client:` runs the lifespan (timers, room sweeper, nightly tasks). The replacements are made on `api_app`. |
| `sent_emails`             | each test    | List of the emails "sent" during the test (`Email`: recipient, subject, text, HTML). FastAPI background tasks run before `TestClient` returns the response, so the list is complete right after the request. `link_token(email)` (`tests/integration/helpers.py`) extracts the token of the link it contains.                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `stored_images`           | each test    | Images "stored" during the test, by storage key. Their URLs start with `FAKE_IMAGE_BASE_URL` (`https://images.example.com`). `FakeImageStorage` moves the file of a hidden image under `quarantine_key(key)` (`quarantine/{key}`) and back (`copy_to_quarantine`, `copy_from_quarantine`), and signs a preview URL as `FAKE_PRESIGNED_BASE_URL/{key}` (`https://signed.example.com`, `presigned_url`).                                                                                                                                                                                                                                                                                                                               |
| `s3_image_storage`        | once per run | The **real** image storage, built from the `IMAGE_S3_*` settings (SeaweedFS of `compose.yaml` locally and on CI). It first deletes a missing key, which does nothing but checks the address, the keys and the bucket; when that fails, the tests are skipped locally and fail on CI, like the database ones.                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `auth_client`             | each test    | `client` with settings adapted to `TestClient`: refresh cookie not `Secure`. `TestClient` talks plain HTTP to `http://testserver/api/...` and would otherwise never send the cookie back. The cookie paths keep their real values (`/api/auth`, `/api/rooms`).                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `override_settings`       | each test    | Function that changes settings for one test, e.g. `override_settings(google_login_attempt_ttl_minutes=2)`, on top of `auth_client`. It only reaches settings injected by FastAPI (`Depends(get_settings)`).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `room_events`             | each test    | Replaces the room event publisher with a `RecordingRoomEventPublisher` that keeps the events published by the REST routes (`events`, `types()`) and the sockets they ask to close (`disconnections`, and `closed_rooms` for a closed room), without socket.                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `round_scheduler`         | each test    | Replaces the round timers with a `RecordingRoundScheduler` that keeps the scheduled deadlines (`deadlines`: game, round, end) and cooldown ends (`cooldown_ends`: game, end); the test calls the transition itself (`end_round_on_timer`, `end_cooldown_on_timer`) to simulate the end of a timer.                                                                                                                                                                                                                                                                                                                                                                                                                                   |

**In parallel (`pytest -n auto`)**: pytest-xdist splits the tests among several processes (workers). Each worker gets its own databases, the worker id appended to their names (`tierlist_test_gw0`, `tierlist_test_migrations_gw0`…): it migrates them alone, and its transactions never meet those of the other workers. The S3 tests use unique keys, so they share the bucket. Every worker must collect the same test names: parameters must not be random (e.g. no `uuid4()` in a `parametrize` list). The worker databases stay on the server between runs, like `tierlist_test`. In a worker, `app.main` is imported before pytest captures the output, so the application's log handler would write to the real stderr: the autouse fixture `rebind_app_logs_to_stderr_captured_under_xdist` (`tests/conftest.py`, every test) points it back to the captured stderr, as without xdist. It also covers `test_errors.py`, which calls `configure_logging` again under `capsys`.

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
- **Waiting for an element**: `findBy…` and `waitFor` wait up to **3 s** (`configure({ asyncUtilTimeout: 3000 })` in `src/test/setup.ts`, 1 s by default in Testing Library). A busy machine, such as a CI runner, can take more than 1 s to render a page that works. A passing test does not wait longer: it goes on as soon as the element shows up. 3 s stays below Vitest's test timeout (5 s), so a failure names the missing element. Do not pass a `timeout` to a single wait.
- **Files not isolated** (`isolate: false`, `vite.config.ts`): each Vitest worker keeps its jsdom and its modules from one test file to the next, instead of rebuilding them (about half of the test time). The state they share is reset by `src/test/setup.ts` after each test, after the file's own cleanup: real timers back, the `fetch`/`WebSocket` stubs removed (`vi.unstubAllGlobals`), the access token cleared once the pending responses have settled, the server clock offset back to zero, the stored language and theme forgotten. A test file still restores what it changes otherwise (spies with `mockRestore`, its own module state); no file uses `vi.mock`, whose module mocks would leak to the next files of the worker.
- **Translations**: `src/test/setup.ts` loads the translations (`src/i18n`), switches to French before each test and forgets the stored language after it, so tests check the French texts whatever the jsdom language. A test of another language calls `await i18n.changeLanguage('en')` first.
- **Mocks** (`vi.fn`, `vi.stubGlobal`, `vi.spyOn`): replace a function with a fake whose behavior the test decides. Here, the global `fetch` is replaced by `vi.stubGlobal('fetch', …)` and restored by `vi.unstubAllGlobals()` after each test, so tests **never call the real backend**: they are fast and do not depend on a running server. Everything above `fetch` (API client, TanStack Query hooks, components) runs for real.
- **`renderWithQueryClient`** (`src/test/renderWithQueryClient.tsx`): renders a component inside a **new** TanStack Query client for each test, so no cached data leaks from one test to the next. Retries are disabled (`retry: false`) so error cases fail immediately. Use it instead of `render` for any component that loads data. The `currentUser` option puts an account in the cache of `useCurrentUser`, as the protected routes do in the app, without a `GET /auth/me`. It is cached as loaded at the start of the app (`updatedAt: 0`): a component that asks for `refreshUntilEmailVerified` reads an unconfirmed account again when it mounts.
- **`<dialog>` in jsdom**: jsdom handles the `open` attribute of `<dialog>` but not `showModal()` and `close()`; `src/test/setup.ts` adds a minimal version of both (`close()` also fires the `close` event). The focus trap and the Escape key, handled by the browser, cannot be tested here.
- **Image previews in jsdom**: jsdom has no `URL.createObjectURL`; `src/test/setup.ts` adds one that returns a fake `blob:` address (the image is never decoded in the tests), and an empty `URL.revokeObjectURL`.
- **Theme and `matchMedia`**: jsdom has no `window.matchMedia`, which `src/theme` calls as soon as it loads. `src/test/matchMedia.ts` installs a fake one from `src/test/setup.ts`; `setSystemDark(true)` changes the operating system theme and notifies listeners, like the browser. After each test, `setup.ts` forgets the stored theme, removes the `dark` class from `<html>` and puts the system back to light.
- **`stubBackend`** (`src/test/stubBackend.ts`): replaces `fetch` with a fake backend described route by route (`'GET /auth/me': () => Response.json(alice)`); an undeclared route answers `404`, so an unexpected call makes the test fail, except `POST /auth/refresh`, which answers `204` (no session) unless the test stubs it, so a page that restores the session on load sees a visitor. `calledRoutes` lists the calls received (its `BackendMock` type annotates the mock in the tests), and `alice` (a typed `User`, role `user`), `tokenResponse` and `unauthorized` are ready-made answers. `signedInSession` is the session of a signed-in account (Alice), restored by the refresh token: the app, home page and room tests stub it; `superAdminSession` is the same session for a super admin, and `unverifiedSession` for Alice with an unconfirmed email (`unverifiedAlice`), used by the email banner and editor tests. `errorResponse(status, code, { params, errors })` builds an error in the backend `ErrorResponse` format; the interface translates its `code`. Tests that use the API client also call `setAccessToken(null)` after each test, since the access token is kept in memory by `src/api/client.ts`.
- **`readRepositoryFile`** (`src/test/repositoryFile.ts`): reads a file of the repository, from `frontend/` (the directory `pnpm test` runs in), for the tests that compare the frontend with `backend/` or `index.html`. It uses `node:fs` because Vite refuses `?raw` imports outside `frontend/` and empties the CSS files; `src/test/nodeFs.d.ts` declares only this function, so that the Node types do not reach the application code.
- **`captureSentryEvents`** (`src/test/sentryEvents.ts`): starts the real Sentry SDK with a fake DSN, no default integration (no patched `fetch` or `console`) and a `beforeSend` that keeps each event in the returned array and drops it: nothing leaves the machine. It closes the client when the test ends (`onTestFinished`), since the files share their modules (`isolate: false`). `FAKE_DSN` is also used by `sentry.test.ts`.

### 2.2 Running the tests

| Command (in `frontend/`) | Effect                                          |
| ------------------------ | ----------------------------------------------- |
| `pnpm test`              | Runs all tests once                             |
| `pnpm test:watch`        | Re-runs the affected tests on every file change |
| `pnpm test:coverage`     | All tests, plus a coverage table of `src/`      |

---

## 3. Reading the results

| Result              | Meaning                                                                                                                                                                                              |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `passed` / ✓        | The test ran and every assertion was satisfied.                                                                                                                                                      |
| `failed` / ✗        | An assertion was not satisfied, or an unexpected error was raised. The output shows the expected and actual values.                                                                                  |
| `skipped` (backend) | The test was not run, with the reason in the output (`uv run pytest -rs` lists the reasons). Currently, this happens only for integration tests when PostgreSQL or SeaweedFS is not running locally. |
| `error` (backend)   | A fixture failed before the test could run, e.g. no database on CI.                                                                                                                                  |

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
8. **Update this guide in the same PR** when the way the tests are set up or run changes: a shared fixture, a test helper, a test tool or a command (AGENTS.md §28). A new test only needs a clear name.

---

## 5. CI script tests (`.github/scripts/`)

`.github/scripts/check_docs_sync.py` is run by the **Docs** workflow (`.github/workflows/docs.yml`) on every PR and every push to `develop` and `main`. It checks that:

- every `README.md` and `CHANGELOG.md` has its `.fr.md` version, and the other way round, and each one has its language switcher in its first 5 lines. Every other doc, including everything under `docs/`, `.github/` and `.claude/`, is English-only;
- on a PR only: an English README or CHANGELOG never changes without its French version (and the other way round).

For a justified exception (e.g. a typo fixed in one language of a README), add the `skip-docs-sync` label to the PR and explain why in its description: the PR checks are skipped, the pairing checks still run.

Its tests use `unittest` (standard library, nothing to install) and run first in the same job. Locally, from the repo root: `python -m unittest discover -s .github/scripts`, then `python .github/scripts/check_docs_sync.py --base origin/develop`.

`.github/scripts/junit_summary.py` builds the test report of the CI. Its tests run in the same `unittest` run.

`.github/scripts/write_env.py` writes the pod `.env` in the Deploy workflow ([deployment guide](deployment.md#3-environment-variables-pod-env)). Its tests run in the same `unittest` run.

`.github/scripts/restart_pod.sh` restarts the pod in the Deploy workflow, through the MineStrator panel API ([deployment guide](deployment.md#6-deploying)). Its tests (same `unittest` run) start a local HTTP server standing for the panel, which answers the given statuses and keeps the requests; the retry delay is set to 0 s.

---

## 6. End-to-end tests (Playwright)

The tests above never see the whole app in a real browser: Vitest runs in jsdom with a stubbed backend, a fake WebSocket and an imitated `<dialog>`, and pytest tests the API without a browser. The end-to-end tests drive **Chromium, Firefox and WebKit** (Safari's engine) against the real app, to cover what only a real browser and the real backend do: the HttpOnly session cookie and its refresh, the WebSocket, the drag and drop, the `<dialog>`, the layout, the image storage and the emails.

They stay **few**: a journey is added only when a regression on it would be serious and a Vitest or pytest test cannot see it.

### 6.1 How they run

- **Tool**: [Playwright](https://playwright.dev/) (`@playwright/test`), configured in `frontend/playwright.config.ts`, one project per browser.
- **The app under test**: `frontend/e2e/start-app.ts` (started by Playwright's `webServer`) creates the `tierlist_e2e` database if needed, runs `alembic upgrade head`, then starts uvicorn on `http://127.0.0.1:8100`, serving the API and the frontend build (`frontend/dist`) from **one origin**, as in production. `FRONTEND_BASE_URL` is that origin, so the WebSocket origin check and the email links work; emails go to Mailpit, images to SeaweedFS. The development database is never touched.
- **Data**: each test creates its own accounts (`e2e-<uuid>@e2e.example.com`, a reserved domain) and data, so the tests are independent and run in parallel without resetting the database.
- **Selectors**: roles and accessible names, in French (the default language), as in the Vitest tests.
- **Failures**: on CI, a failed test is retried twice and its trace is kept; locally, `test-results/` keeps the screenshot and the video.
- **On CI**: the `E2E (chromium)`, `E2E (firefox)` and `E2E (webkit)` jobs of `ci.yml` run in parallel whenever the Backend or Frontend job runs (see [CI guide §2](ci.md#2-only-what-a-pr-touches)), and on every push to `develop` and `main`. Each one starts PostgreSQL, Mailpit and SeaweedFS, builds the frontend and runs its browser. The JUnit report (`reports/e2e-junit.xml`) feeds the job summary; when a test fails, the HTML report with its trace, screenshot and video is uploaded as the `e2e-report-<browser>` artifact (14 days). These jobs are not required checks yet: they become required once they have proved stable.

**Run them** (in `frontend/`, with `docker compose up -d --wait` started):

```bash
pnpm exec playwright install chromium firefox webkit   # once
pnpm build                                              # the tests use the build
pnpm test:e2e                                           # every browser
pnpm test:e2e --project=chromium                        # one browser
pnpm test:e2e:ui                                        # interactive mode
```

### 6.2 Helpers (`frontend/e2e/support/`)

| File           | Purpose                                                                                                                                                                                                                                                                                 |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `app.ts`       | Port, URL and database of the app under test, URL of the Mailpit API.                                                                                                                                                                                                                   |
| `accounts.ts`  | `newAccount(name)`: a display name, a unique address on the reserved domain and a random password. `signUp(page, name)`: registers such an account through the page. `grantSuperAdmin(account)`: runs `scripts/set_super_admin.py` on the e2e database.                                 |
| `backend.ts`   | The environment of the app under test and `runInBackend(args)` (`uv run …` in `backend/`), shared by `start-app.ts` and `grantSuperAdmin`.                                                                                                                                              |
| `drag.ts`      | `dragWithMouse(page, source, target)`: presses on the source, moves frame by frame (`requestAnimationFrame`) to the target, then releases. dnd-kit starts a drag after a few pixels and computes the drop target on animation frames; moving all at once often drops nothing on WebKit. |
| `templates.ts` | `createTemplate(page, name, tiles)`: creates a template from "Mes modèles" and adds text tiles.                                                                                                                                                                                         |
| `mailpit.ts`   | `linkSentTo(request, address, path)`: waits for the latest email sent to the address in Mailpit and returns its link to that path.                                                                                                                                                      |
