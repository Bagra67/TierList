# Deployment

English | [Français](deployment.fr.md)

Where TierList runs and how it is deployed automatically, with a **staging** and a **production** environment. Decided in spike #155; **not built yet**: the implementation issues are listed in §5 (milestone Infrastructure).

## 1. Needs and constraints

| Need               | Detail                                                                                                                                                                                      |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend            | FastAPI with **one worker**: the real-time registry is in memory ([real-time guide](realtime.md#29-scaling)). A long-running process, not serverless.                                       |
| WebSocket          | Behind TLS (`wss://`), with an idle timeout longer than the 10 s heartbeat. A redeployment closes the sockets; clients reconnect and read the room again ([WebSocket guide](websocket.md)). |
| Data               | PostgreSQL with Alembic migrations; S3-compatible storage for tile images ([images guide](images.md)).                                                                                      |
| Emails             | SMTP for the verification and password reset emails ([emails guide](emails.md#4-in-production)), with SPF, DKIM and DMARC.                                                                  |
| Frontend           | Static Vite build, on the same origin as the API (`/api`), like in development.                                                                                                             |
| Budget and hosting | A **VPS** is preferred; about **20 €/month** for staging and production together, storage and emails included (product owner, #155).                                                        |

The load is small for now: rooms of 10 participants at most, a few rooms at a time.

## 2. Options considered

Prices checked on **2026-10-16**. Both providers raised their prices in 2026, so check them again when ordering. HT = excluding VAT.

### 2.1 Servers

| Provider      | Plan                   | Size                                   | Price per month                                   | Backups                   | Notes                                                                                                                          |
| ------------- | ---------------------- | -------------------------------------- | ------------------------------------------------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **OVHcloud**  | VPS-1 (range VPS 2026) | 4 vCore, 8 GB RAM, 75 GB, 400 Mbit/s   | 7.79 € without commitment (from 1 April 2026) [1] | Included [2]              | French company, EU data centres, unlimited traffic. Lower prices with a 6 or 12-month commitment.                              |
| Hetzner Cloud | CX23                   | 2 vCPU, 4 GB RAM, 40 GB, 20 TB traffic | 5.49 € HT + 0.50 € IPv4 [3]                       | +20 % of the server price | Hourly billing, good API. At the time of writing, the official pages showed the shared plans as **currently unavailable** [4]. |
| Hetzner Cloud | CX33                   | 4 vCPU, 8 GB RAM, 80 GB, 20 TB traffic | 8.49 € HT + 0.50 € IPv4 [3]                       | +20 %                     | Same availability warning.                                                                                                     |
| Scaleway      | DEV1-S                 | 2 vCPU, 2 GB RAM                       | about 6.55 € HT, storage and IPv4 extra [5]       | Snapshots extra           | 2 GB is tight for PostgreSQL + backend + proxy.                                                                                |

A **managed PostgreSQL** was left out: alone, it would take most of the budget. PostgreSQL runs in a container on the server, with off-site backups (§3.4).

### 2.2 Storage and emails

| Need                    | Option                           | Price                                                             | Notes                                                                                                |
| ----------------------- | -------------------------------- | ----------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Tile images, DB backups | **Scaleway Object Storage**      | 0.01606 €/GB/month HT (multi-AZ), 75 GB egress free per month [6] | S3 API, Paris. Images are small WebP files: a few cents a month. Off-site from the servers.          |
| Tile images             | SeaweedFS on the server          | Server disk                                                       | Already used in development, but then the images share the server's fate and need their own backups. |
| Emails                  | **Scaleway Transactional Email** | 300 emails free per month, then 0.25 € HT per 1,000 [7]           | No subscription, EU. Same account as the storage.                                                    |
| Emails                  | Brevo                            | Free plan: 300 emails per day, SMTP relay [8]                     | Branding in the free plan's emails; to keep in mind if the volume grows.                             |

## 3. Decision

### 3.1 Hosting

- **Two OVHcloud VPS-1**, one for **staging** and one for **production**. Separate machines: a staging deployment or a test can never slow down or break production. With backups included and 8 GB of RAM, it is the best fit for the budget.
- **Alternative**: two Hetzner CX23 servers, if OVHcloud becomes unavailable or too expensive. The setup below stays the same: only the machines change.
- **Scaleway Object Storage**: one bucket per environment for the images (public read), and one private bucket for the database backups.
- **Scaleway Transactional Email** for the emails, with the domain authorised (SPF, DKIM, DMARC).
- **A domain name** is needed: `tierlist.<domain>` for production, `staging.tierlist.<domain>` for staging. Still to choose (§6).

Estimated cost: about **16 €/month** for both servers, plus less than 1 € for storage and emails at the current volume. The domain is extra, yearly.

### 3.2 On each server

```
Internet ──443──> Caddy ──┬── /api/*  ──> backend (uvicorn, 1 worker) ──> PostgreSQL
                          └── /*      ──> frontend (static files)
                                           backend ──> Scaleway S3, Scaleway TEM
```

- **Docker Compose** with three services: `caddy`, `backend`, `postgres`.
- **Caddy**: automatic TLS certificates (Let's Encrypt), WebSocket proxying without extra configuration, serves the frontend build (copied into the Caddy image), strips `/api` before the backend like the Vite proxy does in development.
- **Backend**: uvicorn with **one worker**; Alembic migrations run before it starts (§4).
- **PostgreSQL**: official image, data on a Docker volume, not exposed outside the server.
- **Server hardening**: SSH keys only, firewall open on 22, 80 and 443, automatic security updates.

### 3.3 Configuration and secrets

- One **GitHub environment** per target: `staging` and `production`. Each holds the server address, the SSH deploy key and the application secrets (`JWT_SECRET_KEY`, database password, S3 keys, SMTP, Google OAuth).
- The deployment writes the `.env` of the server from these secrets: GitHub is the only place where they live, and a server can be rebuilt from scratch.
- Per environment: `FRONTEND_BASE_URL`, `GOOGLE_REDIRECT_URI` (HTTPS), `IMAGE_PUBLIC_BASE_URL` (the public bucket), `AUTH_COOKIE_SECURE=true`, a different `JWT_SECRET_KEY`.
- `production` requires a **manual approval** (required reviewer) before each deployment.

### 3.4 Backups

- **Database**: a nightly `pg_dump`, compressed, sent to the private backup bucket. Kept 14 days in production, 3 days in staging. A restore is tested once before the first real users, then after any major PostgreSQL upgrade.
- **Server**: the OVHcloud daily backup (included) allows a full restore of a machine.
- **Images**: they live in object storage, outside the servers.

## 4. Continuous deployment

| Event                                                                      | Target         | Approval |
| -------------------------------------------------------------------------- | -------------- | -------- |
| CI green on a push to `develop` (a merged PR)                              | **staging**    | none     |
| `vX.Y.Z` tag created by the `Release` workflow ([releasing](releasing.md)) | **production** | manual   |

Steps of a deployment workflow (`.github/workflows/deploy.yml`):

1. **Build** the images (`backend`, and `caddy` with the frontend build), push them to the GitHub Container Registry (GHCR) tagged with the commit SHA, plus `vX.Y.Z` for a release.
2. **Connect** to the server over SSH (deploy key, pinned host key), write the `.env`, `docker compose pull`.
3. **Migrate**: `docker compose run --rm backend alembic upgrade head`. If it fails, the deployment stops and the running version stays in place.
4. **Restart**: `docker compose up -d`. Open sockets are closed; clients reconnect on their own.
5. **Check**: `GET /api/health` and `/api/health/db` must answer `200` within a minute; otherwise the workflow fails.

**Rollback**: run the workflow by hand (`workflow_dispatch`) with the previous tag. Migrations must stay compatible with the previous version (add a column first, remove it in a later release), so that a rollback never needs a downgrade.

Production deployments are never concurrent (`concurrency` per environment).

## 5. Implementation issues

Milestone **Infrastructure**:

1. **Production images and Compose file** (#158): backend `Dockerfile`, Caddy image with the frontend build and its `Caddyfile`, `deploy/compose.yaml`, health checks.
2. **Server provisioning** (#159): a documented, repeatable script (users, SSH, firewall, automatic updates, Docker), applied to the staging and production servers.
3. **Staging deployment workflow** (#160): GHCR, SSH, migrations, health checks, `staging` environment.
4. **Production deployment workflow** (#161): triggered by the release tag, manual approval, rollback by `workflow_dispatch`.
5. **Database backups** (#162): nightly `pg_dump` to object storage, retention, documented restore.
6. **Production configuration** (#163): domain and DNS, SMTP (SPF, DKIM, DMARC), Google OAuth redirect URI and consent screen, the remaining points of `TODO.md`.

## 6. Open questions

- **Domain name**: which one, and where it is registered.
- **OVHcloud commitment**: monthly (flexible) or 6 to 12 months (cheaper), once the setup is stable.
- **Monitoring**: an external uptime check is enough at first; to add with #160 or #161 if wanted.

## Sources

Checked on 2026-10-16.

1. Next.ink, [OVHcloud augmente fortement le prix de ses VPS 2026 et IPv4](https://next.ink/225720/ovhcloud-augmente-fortement-le-prix-de-ses-vps-2026-et-ipv4/) (VPS-1: 5.39 € → 7.79 € on 1 April 2026, specifications).
2. VPSBenchmarks, [VPS-1 2026 by OVHcloud](https://www.vpsbenchmarks.com/hosters/ovhcloud/plans/vps-1) (backups included in the VPS 2026 range). To confirm on [ovhcloud.com](https://www.ovhcloud.com/fr/vps/) when ordering.
3. CostGoat, [Hetzner pricing](https://costgoat.com/pricing/hetzner) (updated 5 September 2026; IPv4 +0.50 €, backups +20 %).
4. Hetzner, [Cost-Optimized](https://www.hetzner.com/cloud/cost-optimized/) and [Regular Performance](https://www.hetzner.com/cloud/regular-performance/) plans.
5. Scaleway, [Virtual Instances pricing](https://www.scaleway.com/en/pricing/virtual-instances/).
6. Scaleway, [Storage pricing](https://www.scaleway.com/en/pricing/storage/).
7. Scaleway, [Managed services pricing](https://www.scaleway.com/en/pricing/managed-services/) (Transactional Email).
8. Brevo, [pricing](https://www.brevo.com/pricing/) (free plan limits as reported by third-party reviews).
