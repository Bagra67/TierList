# Deployment

English | [Français](deployment.fr.md)

Where TierList runs and how it is deployed, with a **staging** and a **production** environment. TierList runs on **MineStrator** pods (a Pterodactyl-like panel) behind a **Cloudflare Tunnel**. Milestone Infrastructure: #158 to #163 and #192.

## 1. Architecture

```
Browser ──https──> Cloudflare (TLS) ──tunnel──> cloudflared pod ──http──> TierList pod :SERVER_PORT
                                                                          uvicorn, 1 worker
                                                                          ├── /api/*  API and WebSocket
                                                                          └── /*      frontend build
TierList pod ──> PostgreSQL 17 pod (public IP:port)
             ──> Scaleway Object Storage (tile images), Scaleway Transactional Email (SMTP)
GitHub Actions ──SFTP──> TierList pod          GitHub Actions ──pg_dump──> PostgreSQL pod ──> Scaleway (backups)
```

| Component      | What it is                                                                                                                                                                                                            |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TierList pod   | "Python generic" pod, Python 3.13, 1 core / 2 GB, working directory `/home/container`. It runs **one start command** (`bash start.sh`). No Docker, no SSH shell, no root, no cron: files are exchanged over **SFTP**. |
| PostgreSQL pod | PostgreSQL 17, on another IP, reached over the public network (`POSTGRES_HOST`, `POSTGRES_PORT`).                                                                                                                     |
| Cloudflare     | The tunnel (`cloudflared` pod) ends TLS and forwards HTTP and WebSocket to `<pod IP>:<SERVER_PORT>`. Domains: `tierlist-staging.ladwein.dev` and `tierlist.ladwein.dev`.                                              |
| Scaleway       | Object Storage: one public image bucket per environment ([images guide](images.md)) and one private backup bucket. Transactional Email for the emails ([emails guide](emails.md)).                                    |
| GitHub Actions | Builds the bundle, uploads it to the pod, checks the health; backs up the database every night.                                                                                                                       |

Constraints:

- **One worker**: the real-time registry is in memory ([real-time guide](realtime.md#29-scaling)).
- **The pod port is also reachable directly**, without the tunnel: only the tunnel may announce the real client and scheme (`TRUSTED_PROXY_IPS`, §2.2).
- **WebSocket**: Cloudflare forwards it; the 10 s heartbeat keeps the connection open. A restart closes the sockets; clients reconnect and read the room again ([WebSocket guide](websocket.md)).
- **Uploads**: Cloudflare accepts bodies up to 100 MB, well above `IMAGE_UPLOAD_MAX_BYTES` (10 MiB).

## 2. In the code

| File                                                                | Role                                                                                                                                                                   |
| ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `backend/app/main.py`                                               | `app`, the root application started by uvicorn: mounts the API (`api_app`) under `/api`, serves the frontend, runs the lifespan (timers, room sweeper, nightly tasks). |
| `backend/app/core/frontend.py`                                      | `mount_frontend`: serves the Vite build (§2.1).                                                                                                                        |
| `backend/app/services/nightly_scheduler.py`, `maintenance.py`       | Nightly tasks in the process (§2.3).                                                                                                                                   |
| `deploy/build_bundle.sh`                                            | Builds `tierlist-<version>.tar.gz` (§2.4).                                                                                                                             |
| `deploy/start.sh`                                                   | Start of a version, at the root of the bundle (§2.4).                                                                                                                  |
| `deploy/launcher.sh`                                                | Pod start command, uploaded as `/home/container/start.sh` (§2.4).                                                                                                      |
| `.github/workflows/bundle.yml`, `deploy.yml`, `backup.yml`          | Bundle, deployment (§6, §7) and backups (§8).                                                                                                                          |
| `.github/scripts/write_env.py`, `restart_pod.sh`, `wait_healthy.sh` | Pod `.env` from the GitHub environment, pod restart, health check of the deployment.                                                                                   |

### 2.1 One origin, the API under `/api`

FastAPI serves everything on one origin: no CORS, and the cookies stay `SameSite=Strict`.

- The API is a sub-application **mounted under `/api`** (REST and WebSocket). Its contract (`openapi.json`, `frontend/src/api/schema.d.ts`) keeps paths without `/api`: the frontend client adds it (`baseUrl` = origin + `/api`). The API docs are at `/api/docs`.
- An unknown `/api/...` route answers the API's JSON 404, never `index.html`.
- The Vite build is served from `FRONTEND_DIST` (default `frontend_dist/` next to `backend/`, as in the bundle):
  - `/assets/*`: hashed files, `Cache-Control: public, max-age=31536000, immutable`;
  - a file of the build root (favicon…) is served if it exists; the resolved path must stay inside the build (no `../`);
  - any other path answers `index.html` with `Cache-Control: no-cache`: the frontend router shows the page.
- Without that folder (development, tests), the app starts and serves the API only.
- In development, the Vite proxy forwards `/api` unchanged to port 8000 (`frontend/vite.config.ts`): the same paths as in production.

The public address is `FRONTEND_BASE_URL` (`https://<domain>`): base of the links sent by email, and the only origin accepted by the real-time channel. Nothing uses the host of the request.

### 2.2 Behind the tunnel

uvicorn runs with `--proxy-headers --forwarded-allow-ips "$TRUSTED_PROXY_IPS"`: only these addresses (the tunnel) may set `X-Forwarded-For` and `X-Forwarded-Proto`. **Never `*`**: the port is reachable directly, anyone could then claim any address. `start.sh` refuses to start without the variable, or with `*`.

The scheme seen by the app does not drive anything sensitive: the cookies are `Secure` through `AUTH_COOKIE_SECURE=true`, the redirects after Google sign-in are relative, and the channel origin comes from `FRONTEND_BASE_URL`. The proxy headers keep the logs and `request.url` right.

`/api/health` (no dependency) answers `{"status": "ok", "release": "<APP_RELEASE>"}`; `/api/health/db` also runs `SELECT 1` (`503` when the database does not answer).

### 2.3 Nightly tasks

There is no cron on the pods. The lifespan starts a small scheduler next to the inactive-room sweeper (`nightly_scheduler.py`, same style: an asyncio task, no scheduling library for one run a day):

- every night at `MAINTENANCE_HOUR_UTC` (UTC), it purges the deleted templates, then the unused images (`maintenance.py`, also called by `scripts/purge_*.py` from the command line);
- each task logs its result; an exception is logged without stopping the next tasks, the next nights or the app;
- the purges only delete what has expired: running them twice is harmless;
- `MAINTENANCE_ENABLED=false` turns it off.

### 2.4 Bundle and pod layout

`tierlist-<version>.tar.gz` contains `backend/` (code, Alembic migrations, `alembic.ini`, `pyproject.toml`, `uv.lock`, purge scripts), `frontend_dist/` (Vite build) and `start.sh`. No tests, no `node_modules`, no `.env`.

```
/home/container/
├── start.sh     launcher (deploy/launcher.sh), started by the pod: bash start.sh
├── CURRENT      name of the version to run, written last by the deployment
├── .env         settings, written by the deployment
├── releases/    tierlist-<version>.tar.gz and their extracted folders (the last 3)
├── bin/uv       installed by start.sh
├── .venv/       Python environment, shared by the versions
└── .cache/uv/
```

SFTP can neither extract an archive nor always create a symbolic link: hence `CURRENT` and the launcher. At each start:

1. the launcher reads `CURRENT`, extracts `releases/tierlist-<version>.tar.gz` if needed (into a temporary folder, then renamed), deletes the versions older than the last 3, then runs the bundle's `start.sh`;
2. `start.sh` installs `uv` in `bin/` if it is missing (official installer, or PyPI without `curl`), loads `.env`, then runs `uv sync --frozen --no-dev` with the Python of the pod;
3. `alembic upgrade head`: **if it fails, the script stops and uvicorn does not start**;
4. `uvicorn app.main:app --host 0.0.0.0 --port $SERVER_PORT --workers 1 --proxy-headers --forwarded-allow-ips $TRUSTED_PROXY_IPS` (`SERVER_PORT` comes from the panel; 8000 otherwise);
5. meanwhile, a small background loop (Python `urllib`, no `curl`) waits for `http://127.0.0.1:$SERVER_PORT/api/health` to answer `200`, then prints **once** the exact line `change this part`: the MineStrator panel ("python generic" Pterodactyl egg) considers the pod started when its console shows that line. After 5 minutes without an answer, it gives up with a log line, without stopping the app (the panel then keeps showing the pod as starting).

A restart reuses `uv`, the environment and the extracted version: it is quick and idempotent.

## 3. Environment variables (pod `.env`)

Written by the deployment from the GitHub environment (`write_env.py`): single-quoted, so that no character of a secret is read by the shell; a missing required value stops the deployment. The other settings keep their default ([backend README](../../backend/README.md)).

| Variable                                                         | GitHub   | Value                                                                               |
| ---------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------- |
| `APP_RELEASE`                                                    | —        | Written by the deployment: `vX.Y.Z` (production) or `develop-<commit>` (staging).   |
| `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER` | variable | The PostgreSQL pod.                                                                 |
| `POSTGRES_PASSWORD`                                              | secret   | Strong, different per environment.                                                  |
| `JWT_SECRET_KEY`                                                 | secret   | At least 32 characters, different per environment (`openssl rand -base64 48`).      |
| `FRONTEND_BASE_URL`                                              | variable | `https://tierlist-staging.ladwein.dev` or `https://tierlist.ladwein.dev`.           |
| `TRUSTED_PROXY_IPS`                                              | variable | Address(es) the tunnel connects from, comma-separated. Never `*`.                   |
| `IMAGE_S3_ENDPOINT_URL`, `IMAGE_S3_BUCKET`, `IMAGE_S3_REGION`    | variable | e.g. `https://s3.fr-par.scw.cloud`, the image bucket, `fr-par`.                     |
| `IMAGE_S3_ACCESS_KEY_ID`, `IMAGE_S3_SECRET_ACCESS_KEY`           | secret   | Scaleway API key allowed on the image bucket.                                       |
| `IMAGE_PUBLIC_BASE_URL`                                          | variable | Public URL of the image bucket.                                                     |
| `SMTP_HOST`, `SMTP_PORT`, `EMAIL_FROM`                           | variable | Scaleway TEM (`smtp.tem.scaleway.com`, `587`), an address of the authorised domain. |
| `SMTP_USERNAME`, `SMTP_PASSWORD`                                 | secret   | TEM SMTP credentials.                                                               |
| `GOOGLE_CLIENT_ID`, `GOOGLE_REDIRECT_URI`                        | variable | Optional. `https://<domain>/api/auth/google/callback`.                              |
| `GOOGLE_CLIENT_SECRET`                                           | secret   | Optional.                                                                           |
| `LOG_LEVEL`, `MAINTENANCE_ENABLED`, `MAINTENANCE_HOUR_UTC`       | variable | Optional (`INFO`, `true`, `3`).                                                     |
| `AUTH_COOKIE_SECURE`                                             | —        | Always `true` (HTTPS).                                                              |

Not in `.env`: `SERVER_PORT` (given by the panel); `FRONTEND_DIST` keeps its default (`frontend_dist/` of the bundle).

## 4. GitHub environments, secrets and variables

Created by hand in the repository settings (Settings → Environments). Nothing of it is in the repository.

| Environment                           | Protection                       | Secrets                                                                                                                                                                                                                                                  | Variables                                                                                                                                                                                                                                                                                                                                                                                       |
| ------------------------------------- | -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `staging`                             | none                             | `SFTP_HOST`, `SFTP_PORT`, `SFTP_USER`, `SFTP_PASSWORD`, `SFTP_KNOWN_HOSTS`, `POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, `IMAGE_S3_ACCESS_KEY_ID`, `IMAGE_S3_SECRET_ACCESS_KEY`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `GOOGLE_CLIENT_SECRET`\*, `PANEL_API_KEY`\* | `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `FRONTEND_BASE_URL`, `TRUSTED_PROXY_IPS`, `IMAGE_S3_ENDPOINT_URL`, `IMAGE_S3_BUCKET`, `IMAGE_S3_REGION`, `IMAGE_PUBLIC_BASE_URL`, `SMTP_HOST`, `SMTP_PORT`, `EMAIL_FROM`, `GOOGLE_CLIENT_ID`\*, `GOOGLE_REDIRECT_URI`\*, `LOG_LEVEL`\*, `MAINTENANCE_ENABLED`\*, `MAINTENANCE_HOUR_UTC`\*, `PANEL_URL`\*, `PANEL_SERVER_ID`\* |
| `production`                          | **required reviewer**            | same as `staging`                                                                                                                                                                                                                                        | same as `staging`                                                                                                                                                                                                                                                                                                                                                                               |
| `backup-staging`, `backup-production` | none (a nightly run cannot wait) | `BACKUP_POSTGRES_PASSWORD`, `BACKUP_S3_ACCESS_KEY_ID`, `BACKUP_S3_SECRET_ACCESS_KEY`                                                                                                                                                                     | `BACKUP_POSTGRES_HOST`, `BACKUP_POSTGRES_PORT`, `BACKUP_POSTGRES_DB`, `BACKUP_POSTGRES_USER`, `BACKUP_S3_ENDPOINT_URL`, `BACKUP_S3_BUCKET`, `BACKUP_S3_REGION`, `BACKUP_RETENTION_DAYS` (`14` production, `3` staging)                                                                                                                                                                          |

\* Optional. `SFTP_KNOWN_HOSTS`: the line(s) of `ssh-keyscan -p <port> <host>`, checked against the fingerprint shown by the panel; the deployment refuses any other host key. `PANEL_SERVER_ID` / `PANEL_API_KEY`: the pod identifier and an API key of the MineStrator panel, to restart the pod after an upload (§6); `PANEL_URL` defaults to `https://mine.sttr.io`. Without the identifier or the key, the pod is restarted by hand.

## 5. First deployment, step by step

How staging was set up (October 2026). Repeat it for production with the values of §5.9. The concrete values (IP addresses, ports, identifiers, accounts) are not in this public repository: keep them in a private place, with the secrets in a password manager.

### 5.1 MineStrator pods (#159)

In the MineStrator panel, MyBox → **Créer un serveur**, location **Toulouse** for every pod (the only one in Europe; the app and its database must be close):

| Pod                                     | Catalog type                    | Allocation        | Start command                                                                        |
| --------------------------------------- | ------------------------------- | ----------------- | ------------------------------------------------------------------------------------ |
| TierList (one per environment)          | `python generic`, Python 3.13   | 1 core, 2 GB      | `bash start.sh` (Paramètres → Paramètres de démarrage du serveur)                    |
| PostgreSQL (one for both environments)  | `PostgreSQL 17` (experimental)  | 1 core, 2 to 4 GB | given by the type                                                                    |
| cloudflared (one for both environments) | `golang generic` (experimental) | 1 core, 2 GB      | `chmod +x ./cloudflared && ./cloudflared tunnel --no-autoupdate run --token <token>` |

- 2 GB is the smallest allocation the panel offers ("Minimum").
- Leave the Git fields of the `python generic` pod empty: the deployment uploads the bundle over SFTP (§6).
- The pods of one MyBox get **different public IP addresses**: the app reaches PostgreSQL over the public network.
- **"Démarrage" forever**: the panel shows a pod as online only once its console prints the line its type waits for. Both generic types wait for the placeholder `change this part`, which neither uvicorn nor cloudflared prints. The pods work anyway (check `/api/health`), but the panel keeps them "starting". Workaround: print that line in the start command, e.g. `… && echo "change this part" && ./cloudflared …` for the tunnel.

### 5.2 PostgreSQL

1. In the PostgreSQL pod settings, set a long random **Superuser Password** (keep it for administration only, never in GitHub), then start the pod.
2. Its console opens a `psql` session as superuser. One role and one database per environment:

   ```sql
   CREATE ROLE tierlist_staging LOGIN PASSWORD '<long random>';
   CREATE DATABASE tierlist_staging OWNER tierlist_staging;
   REVOKE CONNECT ON DATABASE tierlist_staging FROM PUBLIC;
   ```

   `POSTGRES_PASSWORD` and `BACKUP_POSTGRES_PASSWORD` are the password of this role, not the superuser's.

3. **Exposure**: the pod listens on a public `IP:port`, and the type adds `host all all 0.0.0.0/0 md5` at the end of `postgres_db/pg_hba.conf` (Fichiers). The backups run from GitHub runners (§8), whose addresses change: the database must stay reachable from the Internet. Harden it instead: long passwords, `scram-sha-256` instead of `md5`, and no remote access for the superuser (a `host all postgres 0.0.0.0/0 reject` line before the last one), then `SELECT pg_reload_conf();`.

### 5.3 Domain and Cloudflare

1. The domain `ladwein.dev` is registered at **Cloudflare Registrar** (DNS at Cloudflare, required by the tunnel). Turn on its automatic renewal (Domains → Registrations).
2. **Networking → Tunnels → Create Tunnel** (type cloudflared). Copy the token from the `cloudflared tunnel run --token …` line: it is a secret (it goes only in the start command of the cloudflared pod).
3. Download `cloudflared-linux-amd64` from the [cloudflared releases](https://github.com/cloudflare/cloudflared/releases), rename it `cloudflared` and drop it in the files of the cloudflared pod. Building it through the `GO_PACKAGE` field of the type produced no binary.
4. Once the pod runs, the tunnel shows **Healthy**; its **Origin IP** (Overview → Replicas) is the address it reaches the pods from: `TRUSTED_PROXY_IPS`.
5. **Add route → Published application**: hostname → `http://<TierList pod IP>:<SERVER_PORT>` (main port shown in the panel, Accès). The DNS record is created automatically, WebSocket included.
6. **One level of subdomain only**: the free certificate covers `*.ladwein.dev`, not `*.*.ladwein.dev` (that needs Advanced Certificate Manager). Hence `tierlist-staging.ladwein.dev`, not `staging.tierlist.ladwein.dev`.

### 5.4 Scaleway (#163)

One organization, project **TierList**, region **Paris** (`fr-par`). A payment method is required before ordering anything.

1. **Object Storage**: bucket names are unique across all Scaleway customers, hence a prefix: `ladwein-tierlist-images-<environment>` (one per environment) and `ladwein-tierlist-backups` (shared: each environment writes and prunes under its own prefix, §8). Leave the 90-day trial off.
2. **Public read of the images**: objects are private by default, even in a public bucket, and the console offers no bucket policy. `IMAGE_PUBLIC_BASE_URL` (`https://<bucket>.s3.fr-par.scw.cloud`) only works if each image is uploaded with the `public-read` ACL, or if a bucket policy is set through the API. **Open point**: `image_storage.py` sends no ACL today.
3. **IAM → Applications**: one application per environment (`tierlist-staging`), with a policy limited to the TierList project: `ObjectStorageFullAccess` and `TransactionalEmailFullAccess`. Then **API keys → Generate**: the secret key is shown once.
4. **Transactional Email**: plan **Essential** (pay as you go, 300 emails included), domain `ladwein.dev`. Add its DNS records in Cloudflare (all "DNS only"): TXT SPF on `@`, TXT DKIM on `<project id>._domainkey`, TXT DMARC `v=DMARC1; p=none` on `_dmarc`, MX `10 blackhole.tem.scaleway.com` on `@`. The status turns **Verified** within minutes to hours. The MX makes `@ladwein.dev` unable to receive mail; replace it if an inbox is ever needed.
5. SMTP: `smtp.tem.scaleway.com`, port `587`; `SMTP_USERNAME` = the project identifier, `SMTP_PASSWORD` = the secret key of the IAM application.

### 5.5 Google OAuth

In a Google Cloud project dedicated to TierList: one **OAuth client** (web application) per environment, redirect URI `https://<domain>/api/auth/google/callback`. The secret is shown only at creation. On the consent screen, the app name is what users see; in "Testing" mode only the listed test users can sign in: publish it before opening production.

### 5.6 SFTP and panel API

- SFTP (panel → pod → Accès): `SFTP_HOST` and `SFTP_PORT` **without** `sftp://` (`ssh-keyscan` fails with "Name or service not known" otherwise). `SFTP_KNOWN_HOSTS` = the output of `ssh-keyscan -p <port> <host>`.
- `PANEL_SERVER_ID`: the number in the pod URL (`minestrator.com/my/server/<id>`). `PANEL_API_KEY`: a key created in **Mon compte → Clés API du compte**, used only by the deployment (not a personal key, not the one of another tool): it can then be revoked alone.

### 5.7 GitHub

Settings → Environments: the environments, secrets and variables of §4. The `staging` environment may already exist (created by a first workflow run): fill it in.

### 5.8 First deployment and checks

1. Merge a PR into `develop`: CI, then Deploy (§6). Or re-run the last Deploy run (Actions → Deploy → run → **Re-run all jobs**): a re-run reads the **current** secrets and variables. Running Deploy by hand only accepts a `vX.Y.Z` tag, not `develop`.
2. After changing a secret or a variable, redeploy: the pod `.env` is only written by the deployment.
3. Checks: `/api/health` reports the deployed version; `/api/health/db` answers; the home page shows the sign-in screen; "Continuer avec Google" opens the Google account chooser; sign-up sends the verification email (Scaleway: Email activity); an image upload shows the image; a game between two browsers (WebSocket).
4. The panel console can stop refreshing after "Creating virtual environment": trust `/api/health`, not the console.

### 5.9 Production

Same steps, with:

| Item                    | Staging                                      | Production                                                |
| ----------------------- | -------------------------------------------- | --------------------------------------------------------- |
| TierList pod            | its own                                      | a new `python generic` pod                                |
| Database                | `tierlist_staging` (role and database)       | `tierlist_prod`, same PostgreSQL pod                      |
| Tunnel route            | `tierlist-staging.ladwein.dev` → staging pod | `tierlist.ladwein.dev` → production pod, **same tunnel**  |
| Image bucket            | `ladwein-tierlist-images-staging`            | `ladwein-tierlist-images-production`                      |
| Scaleway application    | `tierlist-staging`                           | `tierlist-production` (its own key)                       |
| Google OAuth client     | staging client                               | production client, consent screen published               |
| GitHub environments     | `staging`, `backup-staging`                  | `production` (**required reviewer**), `backup-production` |
| `BACKUP_RETENTION_DAYS` | `3`                                          | `14`                                                      |
| Secrets                 | —                                            | all different: `JWT_SECRET_KEY`, passwords, keys          |

`TRUSTED_PROXY_IPS` stays the address of the cloudflared pod. Then make a release ([releasing guide](releasing.md)) and approve the deployment.

### 5.10 Backups

Run the Backup workflow by hand once, then try a restore on staging (§8, #162).

### 5.11 Consoles

- MineStrator: [panel](https://minestrator.com/my), [API documentation](https://api.minestrator.com) (base `https://mine.sttr.io`)
- Cloudflare: [dashboard](https://dash.cloudflare.com) (Domains, Networking → Tunnels, DNS)
- Scaleway: [console](https://console.scaleway.com) (Object Storage, IAM, Transactional Email), [storage pricing](https://www.scaleway.com/en/pricing/storage/)
- Google: [Cloud console, credentials](https://console.cloud.google.com/apis/credentials)
- GitHub: repository Settings → Environments, Actions → Deploy / Backup

## 6. Deploying

| Event                                                       | Target         | Version (`APP_RELEASE`) | Approval        |
| ----------------------------------------------------------- | -------------- | ----------------------- | --------------- |
| CI green on a push to `develop` (a merged PR)               | **staging**    | `develop-<commit>`      | none            |
| `Release` workflow done: tag `vX.Y.Z` on `main`             | **production** | `vX.Y.Z`                | required        |
| Run by hand (`workflow_dispatch`): a tag and an environment | either         | the tag                 | per environment |

Production follows the `Release` workflow (`workflow_run`), not `on: push: tags`: Release creates the tag with `GITHUB_TOKEN`, and GitHub starts no workflow for an event made with that token. `workflow_run` and `workflow_dispatch` use `deploy.yml` from the default branch (`develop`).

Steps of `deploy.yml`:

1. **Plan**: environment, commit and version.
2. **Bundle** (`bundle.yml`): ShellCheck on the scripts, `pnpm build`, `deploy/build_bundle.sh`, artifact `tierlist-bundle`.
3. **Upload** over SFTP (password through `sshpass`, pinned host key): `releases/tierlist-<version>.tar.gz`, the launcher as `start.sh`, `.env`, then `CURRENT` last. A failed upload leaves the running version in place.
4. **Restart** (`restart_pod.sh`): through the MineStrator panel API (its own, not the Pterodactyl client API) when `PANEL_SERVER_ID` and `PANEL_API_KEY` are set: `PUT $PANEL_URL/server/<id>/poweraction` with `Authorization: Bearer <key>` and `{"poweraction":"restart"}` (`PANEL_URL` defaults to `https://mine.sttr.io`). `200` means the restart is requested; `400` (wrong pod identifier), `401` (wrong key) or any other answer fails the step with the reason in the job summary; `429` (too many requests) is tried again once after 30 s. Without the identifier or the key, the job summary asks to restart the pod in the panel.
5. **Health** (`wait_healthy.sh`): `/api/health` must report the new version, then `/api/health/db` must answer `200`; 30 tries 5 s apart (120 when the restart is manual). Otherwise the job fails.

One deployment at a time per environment (`concurrency`, a pending one waits).

## 7. Rollback

Run the Deploy workflow by hand with the previous tag and the environment. The bundle is built again from that tag; production still asks for its approval.

Migrations must stay compatible with the previous version (add a column in one release, use it, remove the old one in a later release): a rollback never runs a downgrade ([releasing guide](releasing.md)).

Without GitHub: if the previous archive is still in `releases/` (the last 3 are kept), write its version in `CURRENT` over SFTP, then restart the pod. `.env` keeps the newer `APP_RELEASE` until the next deployment.

## 8. Backups

`backup.yml` runs every night at 02:30 UTC (and by hand), for `staging` and `production`:

1. `pg_dump -Fc` with the PostgreSQL 17 client (`postgres:17-alpine` image on the runner) against the database pod;
2. upload to `s3://<bucket>/<environment>/tierlist-<environment>-<date>.dump` (Scaleway, `aws s3` with `--endpoint-url`);
3. deletion of the dumps older than `BACKUP_RETENTION_DAYS` (14 days in production, 3 in staging).

An environment without `BACKUP_POSTGRES_HOST` is skipped. Limits: the database must be reachable from GitHub (strong password, TLS if the pod offers it), a scheduled run can start late, and the database credentials are stored in GitHub.

Restore (on staging first):

```bash
aws s3 cp --endpoint-url https://s3.fr-par.scw.cloud s3://<bucket>/staging/<dump> backup.dump
docker run --rm -i -e PGPASSWORD postgres:17-alpine \
  pg_restore --clean --if-exists --no-owner -h <host> -p <port> -U <user> -d <db> < backup.dump
```

## 9. What stays manual

- Creating the pods, the tunnel, the DNS records and the Scaleway resources (#159, #163).
- The GitHub environments, secrets and variables (§4), and the `production` reviewer.
- The pod restart, as long as `PANEL_SERVER_ID` and `PANEL_API_KEY` are not set, or when the panel refuses it (set up on staging: the restart is automatic there).
- Redeploying after a change of a secret or a variable (§5.8).
- Approving each production deployment.
- Testing a restore (#162), then after each major PostgreSQL upgrade.

## 10. Trying the production layout locally

```bash
cd frontend && pnpm build && cd ..
bash deploy/build_bundle.sh local bundle     # bundle/tierlist-local.tar.gz
```

Extract it, add a `.env` (with `TRUSTED_PROXY_IPS=127.0.0.1`), then `bash start.sh` in the extracted folder: the frontend, the API and the WebSocket answer on port 8000. Or, from `backend/`, copy `frontend/dist` to `frontend_dist/` at the repository root and run `uv run uvicorn app.main:app`.

## 11. History

Spike #155 had chosen two VPS with Docker Compose and Caddy (TLS, `/api` stripped before the backend). That design was replaced by the MineStrator pods before it was built: the issues #158 to #163 were rewritten accordingly.
