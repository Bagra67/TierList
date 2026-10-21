# TODO

English | [Français](TODO.fr.md)

Manual steps left to do: configuration, checks in a browser, merges and decisions that cannot be done from the code. Tick an item once it is done, and remove a section once it is empty.

## 1. Before the first deployment

- [x] Choose a hosting target: MineStrator pods behind a Cloudflare Tunnel ([deployment guide](docs/technical/deployment.md)).
- [x] Release bundle, pod start script and continuous deployment (#158, #160, #161).
- [x] Create the pods, the tunnel and the GitHub environments, then deploy staging: [first deployment](docs/technical/deployment.md#5-first-deployment-step-by-step) (#159, #163).
- [ ] Same for production ([production](docs/technical/deployment.md#59-production)): production pod, `tierlist_prod` database, `tierlist.ladwein.dev` route, `production` and `backup-production` environments.
- [x] Show the TierList pod as online in the MineStrator panel: `deploy/start.sh` prints `change this part` once the app answers (#197).
- [ ] Same for the tunnel pod: print `change this part` in its start command ([pods](docs/technical/deployment.md#51-minestrator-pods-159)).
- [ ] Harden PostgreSQL: `scram-sha-256`, no remote superuser ([PostgreSQL](docs/technical/deployment.md#52-postgresql)).
- [ ] Production settings (GitHub environments, [deployment guide](docs/technical/deployment.md#4-github-environments-secrets-and-variables)):
  - a `JWT_SECRET_KEY` different from development;
  - `AUTH_COOKIE_SECURE=true` (the default) and HTTPS;
  - a strong `POSTGRES_PASSWORD`.
- [ ] Emails in production ([emails guide](docs/technical/emails.md#4-in-production)): choose an SMTP provider, authorize the domain (SPF, DKIM, DMARC), set `SMTP_*`, `EMAIL_FROM` and `FRONTEND_BASE_URL`. Done on staging: Scaleway Transactional Email, domain `ladwein.dev` verified ([Scaleway](docs/technical/deployment.md#54-scaleway-163)).
- [ ] Limit repeated attempts (sign-in, registration, emails) at the host level (Cloudflare rate limiting rules). The trusted proxy headers are set (`TRUSTED_PROXY_IPS`, `--forwarded-allow-ips`).
- [ ] Google in production: add the HTTPS redirect URI to the OAuth client, set `GOOGLE_REDIRECT_URI` to it, and publish the consent screen (in "Testing" mode, only test users can sign in).
- [x] Purge of deleted templates and unused images every night: in the app process (#192, `MAINTENANCE_ENABLED`).
- [ ] Database backups: configure the `backup-*` environments and try a restore on staging (#162).
- [x] Privacy policy: public `/privacy` page, linked from the footer and the settings panel ([legal pages](docs/technical/legal-pages.md), #200).
- [ ] Terms of use (#201) and in-app export of the account data (#202).
- [ ] Tile images ([images guide](docs/technical/images.md#27-storage-and-serving)), once #81 is built: Scaleway Object Storage, one bucket per environment with public read, the `IMAGE_*` settings in the GitHub environments (done on staging; each image is uploaded with the `public-read` ACL, [Scaleway](docs/technical/deployment.md#54-scaleway-163)); later, a CDN able to **purge one URL** (needed to hide an image).

## 2. Decisions to take

- [ ] Features not available yet ([authentication guide](docs/technical/authentication.md#not-available-yet)): other identity providers (Discord, GitHub…), to add with the first one actually wanted. Rate limiting is planned at the host level (see "Before the first deployment").
- [ ] Design system (accent color, typography, logo), **once the tier list editor and one or two features around it exist**, to design on real screens. Until then: theme tokens only (`bg-primary`, `text-muted-foreground`…), no hard-coded color, so the design system is mostly a change of the variables in `frontend/src/index.css` ([frontend README](frontend/README.md#10-ui-components)). The tier colors (S, A, B…) are decided with the editor, as light and dark tokens.
- [ ] Moving to version 1.0.0 (`scripts/prepare-release.sh --version 1.0.0`), when the API is considered stable.

## 3. Tooling

- [ ] **End-to-end tests (Playwright)**, to set up **with the tier list editor**, not before.
  - _What they add_: today's tests run in Vitest with jsdom, a simulated browser with a stubbed backend. They cannot see what only a real browser does: HttpOnly cookies and the session refresh against the real backend, focus and `Escape` in the `<dialog>` (`src/test/setup.ts` notes jsdom cannot test them), layout, and above all the **drag and drop** of the editor. Playwright drives Chromium, Firefox or WebKit against the running app (backend + PostgreSQL + Mailpit).
  - _Cost_: a CI job that starts PostgreSQL, Mailpit, the backend and the frontend (a few minutes per PR); tests that are slower and sometimes flaky (timing, animations); and maintenance each time a screen changes (selectors, flows).
  - _Recommendation_: **not one test per screen**. A handful of critical journeys ("smoke tests"): register → confirm the email (link read from Mailpit's API) → sign in → sign out, then create a tier list and move items between tiers. Everything else stays in Vitest, which is fast and stable. A journey is added only when a regression on it would be serious and jsdom cannot catch it.
