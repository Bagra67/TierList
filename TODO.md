# TODO

English | [Français](TODO.fr.md)

Manual steps left to do: configuration, checks in a browser, merges and decisions that cannot be done from the code. Tick an item once it is done, and remove a section once it is empty.

## 1. Before the first deployment

- [x] Choose a hosting target: MineStrator pods behind a Cloudflare Tunnel ([deployment guide](docs/technical/deployment.md)).
- [x] Release bundle, pod start script and continuous deployment (#158, #160, #161).
- [x] Create the pods, the tunnel and the GitHub environments, then deploy staging: [first deployment](docs/technical/deployment.md#5-first-deployment-step-by-step) (#159, #163).
- [x] Same for production ([production](docs/technical/deployment.md#59-production)): production pod, `tierlist_prod` database, `tierlist.ladwein.dev` route, `production` and `backup-production` environments.
- [x] Show the TierList pod as online in the MineStrator panel: `deploy/start.sh` prints `change this part` once the app answers (#197).
- [x] Same for the tunnel pod: print `change this part` in its start command ([pods](docs/technical/deployment.md#51-minestrator-pods-159)).
- [ ] Harden PostgreSQL: `scram-sha-256`, no remote superuser ([PostgreSQL](docs/technical/deployment.md#52-postgresql)).
- [x] Production settings (GitHub environments, [deployment guide](docs/technical/deployment.md#4-github-environments-secrets-and-variables)):
  - a `JWT_SECRET_KEY` different from development;
  - `AUTH_COOKIE_SECURE=true` (the default) and HTTPS;
  - a strong `POSTGRES_PASSWORD`.
- [x] Emails in production ([emails guide](docs/technical/emails.md#4-in-production)): choose an SMTP provider, authorize the domain (SPF, DKIM, DMARC), set `SMTP_*`, `EMAIL_FROM` and `FRONTEND_BASE_URL`. Scaleway Transactional Email, domain `ladwein.dev` verified ([Scaleway](docs/technical/deployment.md#54-scaleway-163)).
- [ ] Check whether Cloudflare rate limiting rules exist, otherwise create them: limit repeated attempts (sign-in, registration, emails, room codes: `GET /rooms/{code}` and `POST /rooms/{code}/guests` tell whether a code exists) at the host level (Cloudflare rate limiting rules). Only the tunnel reaches the app, and only it may set the proxy headers (`TRUSTED_PROXY_IPS`).
- [x] Google in production: the HTTPS redirect URI is set (`GOOGLE_REDIRECT_URI`) and the consent screen is published.
- [x] Purge of deleted templates and unused images every night: in the app process (#192, `MAINTENANCE_ENABLED`).
- [ ] Database backups: the `backup-*` environments run every night; try a restore on staging ([backups](docs/technical/deployment.md#8-backups), #162).
- [x] Privacy policy: public `/privacy` page, linked from the footer and the settings panel ([legal pages](docs/technical/legal-pages.md), #200).
- [x] Terms of use: public `/terms` page (#201).
- [ ] In-app export of the account data (#202).
- [x] Tile images ([images guide](docs/technical/images.md#27-storage-and-serving)), once #81 is built: Scaleway Object Storage, one bucket per environment with public read, the `IMAGE_*` settings in the GitHub environments (each image is uploaded with the `public-read` ACL, [Scaleway](docs/technical/deployment.md#54-scaleway-163)).
- [ ] Later, a CDN in front of the images, able to **purge one URL** (needed to hide an image).

## 2. Decisions to take

- [ ] Features not available yet ([authentication guide](docs/technical/authentication.md#not-available-yet)): other identity providers (Discord, GitHub…), to add with the first one actually wanted.
- [x] Design system (accent color, typography, logo), designed on the real screens (#213 to #218): the "Le Plateau" palette in the theme tokens of `frontend/src/index.css`, Anybody for headings and Geist for text, a three-bar logo ([frontend README](frontend/README.md#10-ui-components)). The tier colors stay data of each template: new defaults (`DEFAULT_TIERS`), with a text color computed for contrast.
- [x] Moving to version 1.0.0 (`scripts/prepare-release.sh --version 1.0.0`): released, then v1.1.0.

## 3. Tooling

- [ ] **End-to-end tests (Playwright)**: the next step, now that the tier list editor and its drag and drop exist.
  - _What they add_: today's tests run in Vitest with jsdom, a simulated browser with a stubbed backend. They cannot see what only a real browser does: HttpOnly cookies and the session refresh against the real backend, focus and `Escape` in the `<dialog>` (`src/test/setup.ts` notes jsdom cannot test them), layout, and above all the **drag and drop** of the editor. Playwright drives Chromium, Firefox or WebKit against the running app (backend + PostgreSQL + Mailpit).
  - _Cost_: a CI job that starts PostgreSQL, Mailpit, the backend and the frontend (a few minutes per PR); tests that are slower and sometimes flaky (timing, animations); and maintenance each time a screen changes (selectors, flows).
  - _Recommendation_: **not one test per screen**. A handful of critical journeys ("smoke tests"): register → confirm the email (link read from Mailpit's API) → sign in → sign out, then create a tier list and move items between tiers. Everything else stays in Vitest, which is fast and stable. A journey is added only when a regression on it would be serious and jsdom cannot catch it.
