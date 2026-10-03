# TODO

English | [Français](TODO.fr.md)

Manual steps left to do: configuration, checks in a browser, merges and decisions that cannot be done from the code. Tick an item once it is done, and remove a section once it is empty.

## 1. Local configuration

- [ ] Create `backend/.env` from `backend/.env.example` (if not done yet), and replace:
  - `POSTGRES_PASSWORD` (`changez-moi`);
  - `JWT_SECRET_KEY` with a random key: `uv run python -c "import secrets; print(secrets.token_urlsafe(48))"` (in `backend/`).
- [ ] **Set up Google sign-in** (Google Cloud Console → APIs & Services → Credentials), see [authentication guide](docs/authentication.md#2-technical-design), "Setting up Google":
  1. configure the OAuth consent screen (application name, support email; scopes `openid`, `email`, `profile`), and add your Google account as a test user while the screen is in "Testing" mode;
  2. create an **OAuth client ID** of type **Web application**;
  3. add the authorized redirect URI `http://localhost:5173/api/auth/google/callback` (it must match `GOOGLE_REDIRECT_URI` exactly);
  4. copy the client ID and secret into `backend/.env` (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`), then restart the backend.

## 2. Checks in a browser (`dev.ps1`)

- [ ] **Google sign-in**, once configured:
  - "Continue with Google" creates an account without password and opens the home page;
  - with an email already registered by password, Google sign-in links to that account;
  - cancelling on the Google page shows "Google sign-in cancelled" on `/login`;
  - deleting a Google account more than 5 minutes after sign-in asks to sign in again with Google, then reopens the deletion dialog.
- [ ] **Translations (PR #32)**:
  - with a browser set to English, the interface is in English;
  - the language switcher goes back to French, and the choice survives a reload;
  - registering with a too short password shows "The password must be at least 8 characters long" (in English) / "Le mot de passe doit contenir au moins 8 caractères" (in French);
  - a wrong password on sign-in shows the translated message;
  - `/login?error=google_cancelled` shows the message in both languages.

## 3. Pull requests in progress

- [ ] Review the stack, then mark it ready (`gh pr ready 31`, `gh pr ready 32`).
- [ ] Merge **#31 first, then #32** (squash). Merged alone, #31 shows error messages in English until #32 is merged.

## 4. Release

- [ ] Publish the next release: `develop` contains features not released yet (sign-up and email/password sign-in, account deletion, Google sign-in, translations). Follow [docs/releasing.md](docs/releasing.md): `scripts/prepare-release.sh` on a `chore/release-vX.Y.Z` branch, then the release PR `develop` → `main` with a **merge commit**.
- [ ] After the release, check that `origin/develop` still exists.

## 5. Before the first deployment

- [ ] Choose a hosting target, then write the production Docker images and the deployment (open decision, see [architecture](docs/architecture.md#open-decisions)).
- [ ] Production settings (`backend/.env` or the host's variables):
  - a `JWT_SECRET_KEY` different from development;
  - `AUTH_COOKIE_SECURE=true` (the default) and HTTPS;
  - a strong `POSTGRES_PASSWORD`.
- [ ] Google in production: add the HTTPS redirect URI to the OAuth client, set `GOOGLE_REDIRECT_URI` to it, and publish the consent screen (in "Testing" mode, only test users can sign in).

## 6. Decisions to take

- [ ] UI library (open decision, see [architecture](docs/architecture.md#open-decisions)).
- [ ] Features not available yet ([authentication guide](docs/authentication.md#not-available-yet)): email verification and "forgot password" (need an email service to choose), limiting repeated sign-in attempts, other identity providers.
- [ ] Moving to version 1.0.0 (`scripts/prepare-release.sh --version 1.0.0`), when the API is considered stable.
