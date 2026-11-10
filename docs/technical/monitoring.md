English | [Français](monitoring.fr.md)

# Error monitoring (Sentry)

Production errors, from the backend and from the browser, are sent to **Sentry**, which groups them, keeps their stack trace and emails a new error. Nothing is sent while `SENTRY_DSN` is empty: local runs, tests and the CI never send anything.

The logs themselves (INFO and above) still only go to the pod console ([backend README, Logging](../../backend/README.md#10-logging)).

## 1. What is sent

| Source  | Sent                                                                                                                                                                                                    | Where in the code                                                  |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Backend | Every `ERROR` log, with its exception: the app's `app.*` loggers (unhandled errors logged by `core/errors.py`, answered with a generic 500; nightly task failures), but also uvicorn and the libraries. | `app/core/monitoring.py` (`LoggingIntegration(event_level=ERROR)`) |
| Browser | Rendering crashes caught by the error boundary, with the React component stack.                                                                                                                         | `src/components/ErrorBoundary.tsx` (`componentDidCatch`)           |
| Browser | Failed queries other than 4xx (server error, unreachable backend). Expected 4xx are shown by the page and not sent.                                                                                     | `src/api/queryClient.ts`                                           |
| Browser | Uncaught errors and rejected promises (default integrations of the SDK).                                                                                                                                | `src/monitoring/sentry.ts`                                         |

Each event carries the **release** (`APP_RELEASE`: `vX.Y.Z` or `develop-<commit>`) and the **environment** (`SENTRY_ENVIRONMENT`: `staging` or `production`). Warnings are not sent, to keep the free quota for errors.

## 2. What is not sent

The privacy policy promises error reports without IP address, cookies or typed content. The code enforces it:

- **Backend** (`configure_sentry`): `send_default_pii=False` (no user IP, no cookie), `max_request_body_size="never"` (no request body: passwords, emails), `include_local_variables=False` (no variable of the stack frames), and `remove_request_personal_data`, on errors and on transactions, drops the query string (a Google `code`, an email searched by a moderator), the cookies and every header but `User-Agent` (behind Cloudflare, `Cf-Connecting-Ip` holds the user IP; a `Referer` can hold a password reset token). The database engine has `hide_parameters=True` (`db/session.py`): a SQL error does not copy the values of its query (emails, typed text) into its message.
- **Browser** (`buildSentryOptions`): since SDK v11, `dataCollection` collects by default; `userInfo`, `cookies`, `httpHeaders`, `httpBodies` and `urlQueryParams` are all turned off. `removeUrlFragment` and `removeBreadcrumbUrlFragments` drop the URL fragment from the event and the navigation and request breadcrumbs: the guest personal link carries its token there (`/r/<code>#guest=…`). The console breadcrumbs are off (`withoutConsoleBreadcrumbs`): a console message can hold a query key, such as a searched email. No Session Replay, no tracing.
- **Sentry project**: _Settings → Security & Privacy → Prevent Storing of IP Addresses_ must be on, otherwise the Sentry server records the IP address the browser connects from.

Still sent: the URL path, so room codes (`/r/<code>`) and results links (`/results/<token>`), which are made to be shared and hold no personal data.

Performance tracing is off (`SENTRY_TRACES_SAMPLE_RATE=0`); it can be turned on for the backend without a release.

## 3. How the browser gets its settings

One frontend build serves staging and production, so the browser cannot get its DSN at build time. `main.tsx` calls `initMonitoring()`, which reads the public route `GET /api/client-config` (`{ sentry_dsn, environment, release }`) and starts Sentry only when `sentry_dsn` is set. A DSN is public by design: it only allows sending events to the project.

An error raised before `/api/client-config` answers is not sent.

## 4. Sourcemaps

The JavaScript served is minified; to show readable stack traces, Sentry needs the sourcemaps of the exact build.

- `vite.config.ts` turns on `build.sourcemap: 'hidden'` and `@sentry/vite-plugin` **only when `SENTRY_AUTH_TOKEN` is set**. The plugin uploads the maps for the release `SENTRY_RELEASE`, then deletes the `.map` files from `dist/`: they are never published.
- The `Bundle` workflow builds once per version and passes `SENTRY_AUTH_TOKEN` (secret), `SENTRY_ORG`, `SENTRY_PROJECT` (repository variables) and `SENTRY_RELEASE` (the bundle version, same as `APP_RELEASE`).
- Without the token (local, CI), the build is unchanged and has no maps.

## 5. Setting up Sentry

1. Create the organization in the **EU region** (sentry.io, data stored in Germany), plan _Developer_ (free).
2. Create one **React** project (browser and backend share it; the environment tells staging from production).
3. _Settings → Security & Privacy_: turn on **Prevent Storing of IP Addresses**; keep _Data Scrubber_ on.
4. _Alerts_: an email alert on every new issue.
5. Copy the DSN (_Settings → Client Keys_) into the `SENTRY_DSN` variable of the `staging` and `production` GitHub environments, and set `SENTRY_ENVIRONMENT` to `staging` or `production` ([deployment guide](deployment.md)).
6. Create an organization auth token (_Settings → Auth Tokens_; these tokens can create releases and upload sourcemaps) as the **repository** secret `SENTRY_AUTH_TOKEN`, and the repository variables `SENTRY_ORG` (organization slug) and `SENTRY_PROJECT` (project slug).

Retention on the free plan is 30 days (90 days on the paid plans), as written in the privacy policy: changing plan or retention means updating the policy (`privacy.retention.errorReports`).

## 6. Checking it works

- Locally: put a DSN in `backend/.env`, start the backend and the frontend, stop PostgreSQL (`docker compose stop db`) and call `/api/health/db`: the `Échec de la connexion à la base de données` error appears in Sentry, environment `local`.
- After a deployment: `GET /api/client-config` on the domain returns the DSN, the environment and the release; an error triggered in the app appears in Sentry with that release, and its stack trace points to the source files (`src/...`).

## 7. Tests

`backend/tests/test_monitoring.py`, `frontend/src/monitoring/sentry.test.ts`, and the Sentry cases of `ErrorBoundary.test.tsx` and `queryClient.test.ts`: see the [testing guide](testing.md). They use an in-memory transport or `beforeSend`: no event leaves the machine.
