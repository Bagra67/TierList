# Déploiement

[English](deployment.md) | Français

Où tourne TierList et comment il est déployé, avec un environnement de **staging** et un de **production**. TierList tourne sur des pods **MineStrator** (panel de type Pterodactyl) derrière un **Cloudflare Tunnel**. Milestone Infrastructure : #158 à #163 et #192.

## 1. Architecture

```
Navigateur ──https──> Cloudflare (TLS) ──tunnel──> pod cloudflared ──http──> pod TierList :SERVER_PORT
                                                                             uvicorn, 1 worker
                                                                             ├── /api/*  API et WebSocket
                                                                             └── /*      build du frontend
Pod TierList ──> pod PostgreSQL 17 (IP:port publique)
             ──> Scaleway Object Storage (images des tuiles), Scaleway Transactional Email (SMTP)
GitHub Actions ──SFTP──> pod TierList          GitHub Actions ──pg_dump──> pod PostgreSQL ──> Scaleway (sauvegardes)
```

| Composant      | Ce que c'est                                                                                                                                                                                                                                    |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Pod TierList   | Pod « python generic », Python 3.13, 1 cœur / 2 Go, dossier de travail `/home/container`. Il lance **une seule commande** (`bash start.sh`). Pas de Docker, pas de shell SSH, pas de root, pas de cron : les fichiers s'échangent par **SFTP**. |
| Pod PostgreSQL | PostgreSQL 17, sur une autre IP, joint par le réseau public (`POSTGRES_HOST`, `POSTGRES_PORT`).                                                                                                                                                 |
| Cloudflare     | Le tunnel (pod `cloudflared`) termine le TLS et transmet HTTP et WebSocket à `<IP du pod>:<SERVER_PORT>`. Domaines : `tierlist-staging.ladwein.dev` et `tierlist.ladwein.dev`.                                                                  |
| Scaleway       | Object Storage : un bucket public d'images par environnement ([guide des images](images.fr.md)) et un bucket privé de sauvegardes. Transactional Email pour les emails ([guide des emails](emails.fr.md)).                                      |
| GitHub Actions | Construit le bundle, l'envoie dans le pod, vérifie la santé ; sauvegarde la base chaque nuit.                                                                                                                                                   |

Contraintes :

- **Un seul worker** : le registre temps réel est en mémoire ([guide du temps réel](realtime.fr.md#29-montée-en-charge)).
- **Le port du pod est aussi joignable directement**, sans le tunnel : l'application refuse toute connexion qui ne vient pas du tunnel (`TRUSTED_PROXY_IPS`, §2.2).
- **WebSocket** : Cloudflare le transmet ; le battement de cœur de 10 s garde la connexion ouverte. Un redémarrage ferme les sockets ; les clients se reconnectent et relisent la salle ([guide du WebSocket](websocket.fr.md)).
- **Envois de fichiers** : Cloudflare accepte des corps jusqu'à 100 Mo, bien au-dessus de `IMAGE_UPLOAD_MAX_BYTES` (10 Mio).

## 2. Dans le code

| Fichier                                                             | Rôle                                                                                                                                                                     |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `backend/app/main.py`                                               | `app`, l'application racine lancée par uvicorn : monte l'API (`api_app`) sous `/api`, sert le frontend, lance le lifespan (timers, balayage des salles, tâches de nuit). |
| `backend/app/core/frontend.py`                                      | `mount_frontend` : sert le build Vite (§2.1).                                                                                                                            |
| `backend/app/services/nightly_scheduler.py`, `maintenance.py`       | Tâches de nuit dans le processus (§2.3).                                                                                                                                 |
| `deploy/build_bundle.sh`                                            | Construit `tierlist-<version>.tar.gz` (§2.4).                                                                                                                            |
| `deploy/start.sh`                                                   | Démarrage d'une version, à la racine du bundle (§2.4).                                                                                                                   |
| `deploy/launcher.sh`                                                | Commande de démarrage du pod, envoyée comme `/home/container/start.sh` (§2.4).                                                                                           |
| `.github/workflows/bundle.yml`, `deploy.yml`, `backup.yml`          | Bundle, déploiement (§6, §7) et sauvegardes (§8).                                                                                                                        |
| `.github/scripts/write_env.py`, `restart_pod.sh`, `wait_healthy.sh` | `.env` du pod depuis l'environnement GitHub, redémarrage du pod, vérification de santé du déploiement.                                                                   |

### 2.1 Une seule origine, l'API sous `/api`

FastAPI sert tout sur une seule origine : pas de CORS, et les cookies restent `SameSite=Strict`.

- L'API est une sous-application **montée sous `/api`** (REST et WebSocket). Son contrat (`openapi.json`, `frontend/src/api/schema.d.ts`) garde des chemins sans `/api` : le client du frontend l'ajoute (`baseUrl` = origine + `/api`). La doc de l'API est sur `/api/docs`.
- Une route `/api/...` inconnue répond le 404 JSON de l'API, jamais `index.html`.
- Le build Vite est servi depuis `FRONTEND_DIST` (par défaut `frontend_dist/` à côté de `backend/`, comme dans le bundle) :
  - `/assets/*` : fichiers hashés, `Cache-Control: public, max-age=31536000, immutable` ;
  - un fichier de la racine du build (favicon…) est servi s'il existe ; le chemin résolu doit rester dans le build (pas de `../`) ;
  - tout autre chemin répond `index.html` avec `Cache-Control: no-cache` : le routeur du frontend affiche la page.
- Sans ce dossier (développement, tests), l'application démarre et ne sert que l'API.
- En développement, le proxy Vite transmet `/api` tel quel au port 8000 (`frontend/vite.config.ts`) : les mêmes chemins qu'en production.

L'adresse publique est `FRONTEND_BASE_URL` (`https://<domaine>`) : base des liens envoyés par email, et seule origine acceptée par le canal temps réel. Rien n'utilise l'hôte de la requête.

### 2.2 Derrière le tunnel

Le port du pod est public (`<IP du pod>:<port>` répond sans Cloudflare), et l'hébergeur n'offre pas de pare-feu dessus : l'application le ferme elle-même. Quand `TRUSTED_PROXY_IPS` est défini (adresses IP ou réseaux CIDR, séparés par des virgules), `TrustedProxyMiddleware` (`app/core/proxy.py`), la couche la plus externe de l'application racine, regarde l'adresse de la connexion TCP, pas un en-tête :

- les adresses du tunnel sont servies, et elles seules peuvent poser `X-Forwarded-For` et `X-Forwarded-Proto` (`ProxyHeadersMiddleware` d'uvicorn, appliqué à l'intérieur) ;
- la boucle locale (`127.0.0.1`, `::1`) est servie, sans lire ses en-têtes de proxy : la boucle d'attente de `start.sh` l'appelle depuis le pod ;
- toute autre requête HTTP reçoit `403` au format d'erreur de l'API (`code: http_error`) ; une poignée de main WebSocket reçoit aussi `403`.

uvicorn est donc lancé avec `--no-proxy-headers` : sa propre lecture des en-têtes de proxy remplacerait l'adresse de la connexion par le client annoncé avant que l'application la voie. **Jamais `*`** : les réglages le refusent, comme toute valeur qui n'est ni une adresse ni un réseau, et `start.sh` refuse de démarrer sans la variable. Sans elle (développement, tests), tout est servi, comme avant.

Si le pod cloudflared change d'adresse, le site répond `403` partout jusqu'à la mise à jour de `TRUSTED_PROXY_IPS` et un nouveau déploiement (§4).

Le schéma vu par l'application ne pilote rien de sensible : les cookies sont `Secure` grâce à `AUTH_COOKIE_SECURE=true`, les redirections après la connexion Google sont relatives, et l'origine du canal vient de `FRONTEND_BASE_URL`. Les en-têtes du proxy gardent justes les journaux et `request.url`.

`/api/health` (sans dépendance) répond `{"status": "ok", "release": "<APP_RELEASE>"}` ; `/api/health/db` lance en plus `SELECT 1` (`503` si la base ne répond pas).

### 2.3 Tâches de nuit

Il n'y a pas de cron dans les pods. Le lifespan lance un petit planificateur à côté du balayage des salles inactives (`nightly_scheduler.py`, même style : une tâche asyncio, sans bibliothèque de planification pour une exécution par jour) :

- chaque nuit à `MAINTENANCE_HOUR_UTC` (UTC), il purge les templates supprimés, puis les images inutilisées (`maintenance.py`, appelé aussi par `scripts/purge_*.py` en ligne de commande) ;
- chaque tâche journalise son résultat ; une exception est journalisée sans arrêter les tâches suivantes, les nuits suivantes ni l'application ;
- les purges ne suppriment que ce qui a expiré : les lancer deux fois ne pose aucun problème ;
- `MAINTENANCE_ENABLED=false` le désactive.

### 2.4 Bundle et organisation du pod

`tierlist-<version>.tar.gz` contient `backend/` (code, migrations Alembic, `alembic.ini`, `pyproject.toml`, `uv.lock`, scripts de purge), `frontend_dist/` (build Vite) et `start.sh`. Ni tests, ni `node_modules`, ni `.env`.

```
/home/container/
├── start.sh     lanceur (deploy/launcher.sh), lancé par le pod : bash start.sh
├── CURRENT      nom de la version à lancer, écrit en dernier par le déploiement
├── .env         réglages, écrits par le déploiement
├── releases/    tierlist-<version>.tar.gz et leurs dossiers extraits (les 3 dernières)
├── bin/uv       installé par start.sh
├── .venv/       environnement Python, partagé par les versions
└── .cache/uv/
```

SFTP ne sait ni extraire une archive ni toujours créer un lien symbolique : d'où `CURRENT` et le lanceur. À chaque démarrage :

1. le lanceur lit `CURRENT`, extrait `releases/tierlist-<version>.tar.gz` si besoin (dans un dossier temporaire, puis renommé), supprime les versions plus anciennes que les 3 dernières, puis lance le `start.sh` du bundle ;
2. `start.sh` installe `uv` dans `bin/` s'il manque (installeur officiel, ou PyPI sans `curl`), charge `.env`, puis lance `uv sync --frozen --no-dev` avec le Python du pod ;
3. `alembic upgrade head` : **en cas d'échec, le script s'arrête et uvicorn ne démarre pas** ;
4. `uvicorn app.main:app --host 0.0.0.0 --port $SERVER_PORT --workers 1 --no-proxy-headers` (`SERVER_PORT` vient du panel ; 8000 sinon ; l'application lit `TRUSTED_PROXY_IPS`, §2.2) ;
5. pendant ce temps, une petite boucle en arrière-plan (Python `urllib`, sans `curl`) attend que `http://127.0.0.1:$SERVER_PORT/api/health` réponde `200`, puis affiche **une seule fois** la ligne exacte `change this part` : le panel MineStrator (egg Pterodactyl « python generic ») considère le pod démarré quand sa console affiche cette ligne. Après 5 minutes sans réponse, elle abandonne avec une ligne de log, sans arrêter l'application (le panel montre alors toujours le pod en démarrage).

Un redémarrage réutilise `uv`, l'environnement et la version extraite : il est rapide et idempotent.

## 3. Variables d'environnement (`.env` du pod)

Écrites par le déploiement depuis l'environnement GitHub (`write_env.py`) : entre apostrophes, pour qu'aucun caractère d'un secret ne soit interprété par le shell ; une valeur obligatoire absente arrête le déploiement. Les autres réglages gardent leur valeur par défaut ([README du backend](../../backend/README.fr.md)).

| Variable                                                         | GitHub   | Valeur                                                                             |
| ---------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------- |
| `APP_RELEASE`                                                    | —        | Écrite par le déploiement : `vX.Y.Z` (production) ou `develop-<commit>` (staging). |
| `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER` | variable | Le pod PostgreSQL.                                                                 |
| `POSTGRES_PASSWORD`                                              | secret   | Robuste, différent par environnement.                                              |
| `JWT_SECRET_KEY`                                                 | secret   | Au moins 32 caractères, différente par environnement (`openssl rand -base64 48`).  |
| `FRONTEND_BASE_URL`                                              | variable | `https://tierlist-staging.ladwein.dev` ou `https://tierlist.ladwein.dev`.          |
| `TRUSTED_PROXY_IPS`                                              | variable | Adresse(s) d'où se connecte le tunnel, séparées par des virgules. Jamais `*`.      |
| `IMAGE_S3_ENDPOINT_URL`, `IMAGE_S3_BUCKET`, `IMAGE_S3_REGION`    | variable | ex. `https://s3.fr-par.scw.cloud`, le bucket d'images, `fr-par`.                   |
| `IMAGE_S3_ACCESS_KEY_ID`, `IMAGE_S3_SECRET_ACCESS_KEY`           | secret   | Clé d'API Scaleway autorisée sur le bucket d'images.                               |
| `IMAGE_PUBLIC_BASE_URL`                                          | variable | URL publique du bucket d'images.                                                   |
| `SMTP_HOST`, `SMTP_PORT`, `EMAIL_FROM`                           | variable | Scaleway TEM (`smtp.tem.scaleway.com`, `587`), une adresse du domaine autorisé.    |
| `SMTP_USERNAME`, `SMTP_PASSWORD`                                 | secret   | Identifiants SMTP de TEM.                                                          |
| `GOOGLE_CLIENT_ID`, `GOOGLE_REDIRECT_URI`                        | variable | Facultatifs. `https://<domaine>/api/auth/google/callback`.                         |
| `GOOGLE_CLIENT_SECRET`                                           | secret   | Facultatif.                                                                        |
| `LOG_LEVEL`, `MAINTENANCE_ENABLED`, `MAINTENANCE_HOUR_UTC`       | variable | Facultatifs (`INFO`, `true`, `3`).                                                 |
| `AUTH_COOKIE_SECURE`                                             | —        | Toujours `true` (HTTPS).                                                           |

Absents du `.env` : `SERVER_PORT` (donné par le panel) ; `FRONTEND_DIST` garde sa valeur par défaut (`frontend_dist/` du bundle).

## 4. Environnements, secrets et variables GitHub

Créés à la main dans les réglages du dépôt (Settings → Environments). Rien de tout cela n'est dans le dépôt.

| Environnement                         | Protection                                          | Secrets                                                                                                                                                                                                                                                  | Variables                                                                                                                                                                                                                                                                                                                                                                                       |
| ------------------------------------- | --------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `staging`                             | aucune                                              | `SFTP_HOST`, `SFTP_PORT`, `SFTP_USER`, `SFTP_PASSWORD`, `SFTP_KNOWN_HOSTS`, `POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, `IMAGE_S3_ACCESS_KEY_ID`, `IMAGE_S3_SECRET_ACCESS_KEY`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `GOOGLE_CLIENT_SECRET`\*, `PANEL_API_KEY`\* | `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `FRONTEND_BASE_URL`, `TRUSTED_PROXY_IPS`, `IMAGE_S3_ENDPOINT_URL`, `IMAGE_S3_BUCKET`, `IMAGE_S3_REGION`, `IMAGE_PUBLIC_BASE_URL`, `SMTP_HOST`, `SMTP_PORT`, `EMAIL_FROM`, `GOOGLE_CLIENT_ID`\*, `GOOGLE_REDIRECT_URI`\*, `LOG_LEVEL`\*, `MAINTENANCE_ENABLED`\*, `MAINTENANCE_HOUR_UTC`\*, `PANEL_URL`\*, `PANEL_SERVER_ID`\* |
| `production`                          | **relecteur obligatoire**                           | comme `staging`                                                                                                                                                                                                                                          | comme `staging`                                                                                                                                                                                                                                                                                                                                                                                 |
| `backup-staging`, `backup-production` | aucune (une exécution de nuit ne peut pas attendre) | `BACKUP_POSTGRES_PASSWORD`, `BACKUP_S3_ACCESS_KEY_ID`, `BACKUP_S3_SECRET_ACCESS_KEY`                                                                                                                                                                     | `BACKUP_POSTGRES_HOST`, `BACKUP_POSTGRES_PORT`, `BACKUP_POSTGRES_DB`, `BACKUP_POSTGRES_USER`, `BACKUP_S3_ENDPOINT_URL`, `BACKUP_S3_BUCKET`, `BACKUP_S3_REGION`, `BACKUP_RETENTION_DAYS` (`14` en production, `3` en staging)                                                                                                                                                                    |

\* Facultatif. `SFTP_KNOWN_HOSTS` : la ou les lignes de `ssh-keyscan -p <port> <hôte>`, vérifiées avec l'empreinte affichée par le panel ; le déploiement refuse toute autre clé d'hôte. `PANEL_SERVER_ID` / `PANEL_API_KEY` : l'identifiant du pod et une clé d'API du panel MineStrator, pour redémarrer le pod après un envoi (§6) ; `PANEL_URL` vaut par défaut `https://mine.sttr.io`. Sans l'identifiant ou la clé, le pod est redémarré à la main.

## 5. Premier déploiement, pas à pas

Comment le staging a été mis en place (octobre 2026). À refaire pour la production avec les valeurs du §5.9. Les valeurs concrètes (adresses IP, ports, identifiants, comptes) ne sont pas dans ce dépôt public : les garder dans un endroit privé, avec les secrets dans un gestionnaire de mots de passe.

### 5.1 Pods MineStrator (#159)

Dans le panel MineStrator, MyBox → **Créer un serveur**, localisation **Toulouse** pour tous les pods (la seule en Europe ; l'application et sa base doivent être proches) :

| Pod                                           | Type du catalogue               | Allocation       | Commande de démarrage                                                                |
| --------------------------------------------- | ------------------------------- | ---------------- | ------------------------------------------------------------------------------------ |
| TierList (un par environnement)               | `python generic`, Python 3.13   | 1 cœur, 2 Go     | `bash start.sh` (Paramètres → Paramètres de démarrage du serveur)                    |
| PostgreSQL (un pour les deux environnements)  | `PostgreSQL 17` (expérimental)  | 1 cœur, 2 à 4 Go | fournie par le type                                                                  |
| cloudflared (un pour les deux environnements) | `golang generic` (expérimental) | 1 cœur, 2 Go     | `chmod +x ./cloudflared && ./cloudflared tunnel --no-autoupdate run --token <token>` |

- 2 Go est la plus petite allocation proposée par le panel (« Minimum »).
- Laisser vides les champs Git du pod `python generic` : le déploiement envoie le bundle par SFTP (§6).
- Les pods d'une même MyBox ont des **adresses IP publiques différentes** : l'application joint PostgreSQL par le réseau public.
- **« Démarrage » à l'infini** : le panel n'affiche un pod en ligne qu'une fois que sa console affiche la ligne attendue par son type. Les deux types génériques attendent la valeur d'exemple `change this part`, qu'uvicorn et cloudflared n'affichent jamais. Les pods fonctionnent quand même (vérifier `/api/health`), mais le panel les laisse « en démarrage ». Le pod TierList l'affiche lui-même dès que `/api/health` répond (`deploy/start.sh`, §2.4). Pour le tunnel, l'afficher dans la commande de démarrage, par exemple `… && echo "change this part" && ./cloudflared …`.

### 5.2 PostgreSQL

1. Dans les paramètres du pod PostgreSQL, définir un **Superuser Password** long et aléatoire (réservé à l'administration, jamais dans GitHub), puis démarrer le pod.
2. Sa console ouvre une session `psql` en superutilisateur. Un rôle et une base par environnement :

   ```sql
   CREATE ROLE tierlist_staging LOGIN PASSWORD '<long et aléatoire>';
   CREATE DATABASE tierlist_staging OWNER tierlist_staging;
   REVOKE CONNECT ON DATABASE tierlist_staging FROM PUBLIC;
   ```

   `POSTGRES_PASSWORD` et `BACKUP_POSTGRES_PASSWORD` sont le mot de passe de ce rôle, pas celui du superutilisateur.

3. **Exposition** : le pod écoute sur une `IP:port` publique, et le type ajoute `host all all 0.0.0.0/0 md5` à la fin de `postgres_db/pg_hba.conf` (Fichiers). Les sauvegardes partent des runners GitHub (§8), dont les adresses changent : la base doit rester joignable depuis Internet. La durcir plutôt : mots de passe longs, `scram-sha-256` au lieu de `md5`, et pas d'accès distant pour le superutilisateur (une ligne `host all postgres 0.0.0.0/0 reject` avant la dernière), puis `SELECT pg_reload_conf();`.

### 5.3 Domaine et Cloudflare

1. Le domaine `ladwein.dev` est enregistré chez **Cloudflare Registrar** (DNS chez Cloudflare, exigé par le tunnel). Activer son renouvellement automatique (Domains → Registrations).
2. **Networking → Tunnels → Create Tunnel** (type cloudflared). Copier le token de la ligne `cloudflared tunnel run --token …` : c'est un secret (il ne va que dans la commande de démarrage du pod cloudflared).
3. Télécharger `cloudflared-linux-amd64` depuis les [releases de cloudflared](https://github.com/cloudflare/cloudflared/releases), le renommer `cloudflared` et le déposer dans les fichiers du pod cloudflared. Le compiler par le champ `GO_PACKAGE` du type n'a produit aucun binaire.
4. Une fois le pod lancé, le tunnel affiche **Healthy** ; son **Origin IP** (Overview → Replicas) est l'adresse depuis laquelle il joint les pods : `TRUSTED_PROXY_IPS`.
5. **Add route → Published application** : nom d'hôte → `http://<IP du pod TierList>:<SERVER_PORT>` (port principal affiché dans le panel, Accès). L'enregistrement DNS est créé automatiquement, WebSocket compris.
6. **Un seul niveau de sous-domaine** : le certificat gratuit couvre `*.ladwein.dev`, pas `*.*.ladwein.dev` (il faudrait Advanced Certificate Manager). D'où `tierlist-staging.ladwein.dev`, et non `staging.tierlist.ladwein.dev`.

### 5.4 Scaleway (#163)

Une organisation, projet **TierList**, région **Paris** (`fr-par`). Un moyen de paiement est exigé avant de commander quoi que ce soit.

1. **Object Storage** : les noms de bucket sont uniques chez tous les clients Scaleway, d'où un préfixe : `ladwein-tierlist-images-<environnement>` (un par environnement) et `ladwein-tierlist-backups` (partagé : chaque environnement écrit et nettoie sous son propre préfixe, §8). Laisser l'essai de 90 jours désactivé.
2. **Lecture publique des images** : les objets sont privés par défaut, même dans un bucket public, et la console ne propose pas de bucket policy. `IMAGE_PUBLIC_BASE_URL` (`https://<bucket>.s3.fr-par.scw.cloud`) ne fonctionne que si chaque image est envoyée avec l'ACL `public-read`, ou si une bucket policy est posée par l'API. `image_storage.py` envoie chaque image avec l'ACL `public-read` (`IMAGE_ACL`).
3. **IAM → Applications** : une application par environnement (`tierlist-staging`), avec une politique limitée au projet TierList : `ObjectStorageFullAccess` et `TransactionalEmailFullAccess`. Puis **API keys → Generate** : la clé secrète ne s'affiche qu'une fois.
4. **Transactional Email** : offre **Essential** (à l'usage, 300 emails inclus), domaine `ladwein.dev`. Ajouter ses enregistrements DNS dans Cloudflare (tous en « DNS only ») : TXT SPF sur `@`, TXT DKIM sur `<id du projet>._domainkey`, TXT DMARC `v=DMARC1; p=none` sur `_dmarc`, MX `10 blackhole.tem.scaleway.com` sur `@`. Le statut passe à **Verified** en quelques minutes à quelques heures. Le MX empêche `@ladwein.dev` de recevoir des emails ; le remplacer si une boîte de réception devient nécessaire.
5. SMTP : `smtp.tem.scaleway.com`, port `587` ; `SMTP_USERNAME` = l'identifiant du projet, `SMTP_PASSWORD` = la clé secrète de l'application IAM.

### 5.5 Google OAuth

Dans un projet Google Cloud dédié à TierList : un **client OAuth** (application Web) par environnement, URI de redirection `https://<domaine>/api/auth/google/callback`. Le secret ne s'affiche qu'à la création. Sur l'écran de consentement, le nom de l'application est ce que voient les utilisateurs ; en mode « Test », seuls les utilisateurs test listés peuvent se connecter : le publier avant d'ouvrir la production.

### 5.6 SFTP et API du panel

- SFTP (panel → pod → Accès) : `SFTP_HOST` et `SFTP_PORT` **sans** `sftp://` (sinon `ssh-keyscan` échoue avec « Name or service not known »). `SFTP_KNOWN_HOSTS` = la sortie de `ssh-keyscan -p <port> <hôte>`.
- `PANEL_SERVER_ID` : le nombre dans l'URL du pod (`minestrator.com/my/server/<id>`). `PANEL_API_KEY` : une clé créée dans **Mon compte → Clés API du compte**, utilisée seulement par le déploiement (ni une clé personnelle, ni celle d'un autre outil) : elle peut alors être révoquée seule.

### 5.7 GitHub

Settings → Environments : les environnements, secrets et variables du §4. L'environnement `staging` peut déjà exister (créé par une première exécution du workflow) : le compléter.

### 5.8 Premier déploiement et vérifications

1. Merger une PR dans `develop` : CI, puis Deploy (§6). Ou relancer la dernière exécution de Deploy (Actions → Deploy → exécution → **Re-run all jobs**) : une relance lit les secrets et variables **actuels**. Lancer Deploy à la main n'accepte qu'un tag `vX.Y.Z`, pas `develop`.
2. Après avoir changé un secret ou une variable, redéployer : le `.env` du pod n'est écrit que par le déploiement.
3. Vérifications : `/api/health` annonce la version déployée ; `/api/health/db` répond ; la page d'accueil affiche l'écran de connexion ; « Continuer avec Google » ouvre le choix de compte Google ; l'inscription envoie l'email de vérification (Scaleway : Email activity) ; un envoi d'image affiche l'image ; une partie entre deux navigateurs (WebSocket).
4. La console du panel peut cesser de se rafraîchir après « Creating virtual environment » : se fier à `/api/health`, pas à la console.

### 5.9 Production

Mêmes étapes, avec :

| Élément                 | Staging                                      | Production                                                    |
| ----------------------- | -------------------------------------------- | ------------------------------------------------------------- |
| Pod TierList            | le sien                                      | un nouveau pod `python generic`                               |
| Base                    | `tierlist_staging` (rôle et base)            | `tierlist_prod`, même pod PostgreSQL                          |
| Route du tunnel         | `tierlist-staging.ladwein.dev` → pod staging | `tierlist.ladwein.dev` → pod de production, **même tunnel**   |
| Bucket d'images         | `ladwein-tierlist-images-staging`            | `ladwein-tierlist-images-production`                          |
| Application Scaleway    | `tierlist-staging`                           | `tierlist-production` (sa propre clé)                         |
| Client Google OAuth     | client de staging                            | client de production, écran de consentement publié            |
| Environnements GitHub   | `staging`, `backup-staging`                  | `production` (**relecteur obligatoire**), `backup-production` |
| `BACKUP_RETENTION_DAYS` | `3`                                          | `14`                                                          |
| Secrets                 | —                                            | tous différents : `JWT_SECRET_KEY`, mots de passe, clés       |

`TRUSTED_PROXY_IPS` reste l'adresse du pod cloudflared. Puis faire une release ([guide des releases](releasing.fr.md)) et approuver le déploiement.

### 5.10 Sauvegardes

Lancer une fois le workflow Backup à la main, puis essayer une restauration sur le staging (§8, #162).

### 5.11 Consoles

- MineStrator : [panel](https://minestrator.com/my), [documentation de l'API](https://api.minestrator.com) (base `https://mine.sttr.io`)
- Cloudflare : [tableau de bord](https://dash.cloudflare.com) (Domains, Networking → Tunnels, DNS)
- Scaleway : [console](https://console.scaleway.com) (Object Storage, IAM, Transactional Email), [tarifs du stockage](https://www.scaleway.com/en/pricing/storage/)
- Google : [console Cloud, identifiants](https://console.cloud.google.com/apis/credentials)
- GitHub : Settings → Environments du dépôt, Actions → Deploy / Backup

## 6. Déployer

| Événement                                                          | Cible          | Version (`APP_RELEASE`) | Approbation           |
| ------------------------------------------------------------------ | -------------- | ----------------------- | --------------------- |
| CI verte sur un push dans `develop` (une PR mergée)                | **staging**    | `develop-<commit>`      | aucune                |
| Workflow `Release` terminé : tag `vX.Y.Z` sur `main`               | **production** | `vX.Y.Z`                | obligatoire           |
| Lancé à la main (`workflow_dispatch`) : un tag et un environnement | au choix       | le tag                  | selon l'environnement |

La production suit le workflow `Release` (`workflow_run`), pas `on: push: tags` : Release crée le tag avec `GITHUB_TOKEN`, et GitHub ne lance aucun workflow pour un événement fait avec ce jeton. `workflow_run` et `workflow_dispatch` utilisent le `deploy.yml` de la branche par défaut (`develop`).

Étapes de `deploy.yml` :

1. **Planifier** : environnement, commit et version.
2. **Bundle** (`bundle.yml`) : ShellCheck sur les scripts, `pnpm build`, `deploy/build_bundle.sh`, artefact `tierlist-bundle`.
3. **Envoi** par SFTP (mot de passe via `sshpass`, clé d'hôte épinglée) : `releases/tierlist-<version>.tar.gz`, le lanceur sous le nom `start.sh`, `.env`, puis `CURRENT` en dernier. Un envoi raté laisse la version en cours en place.
4. **Redémarrage** (`restart_pod.sh`) : par l'API du panel MineStrator (la sienne, pas l'API client de Pterodactyl) quand `PANEL_SERVER_ID` et `PANEL_API_KEY` sont définis : `PUT $PANEL_URL/server/<id>/poweraction` avec `Authorization: Bearer <clé>` et `{"poweraction":"restart"}` (`PANEL_URL` vaut par défaut `https://mine.sttr.io`). `200` signifie que le redémarrage est demandé ; `400` (mauvais identifiant de pod), `401` (mauvaise clé) ou toute autre réponse fait échouer l'étape, avec la raison dans le résumé du job ; `429` (trop de requêtes) est retenté une fois après 30 s. Sans l'identifiant ou la clé, le résumé du job demande de redémarrer le pod dans le panel.
5. **Santé** (`wait_healthy.sh`) : `/api/health` doit annoncer la nouvelle version, puis `/api/health/db` répondre `200` ; 30 essais espacés de 5 s (120 si le redémarrage est manuel). Sinon le job échoue.

Un seul déploiement à la fois par environnement (`concurrency`, un déploiement en attente patiente).

## 7. Retour arrière

Lancer le workflow Deploy à la main avec le tag précédent et l'environnement. Le bundle est reconstruit depuis ce tag ; la production demande toujours son approbation.

Les migrations doivent rester compatibles avec la version précédente (ajouter une colonne dans une release, s'en servir, retirer l'ancienne dans une release suivante) : un retour arrière ne lance jamais de downgrade ([guide des releases](releasing.fr.md)).

Sans GitHub : si l'archive précédente est encore dans `releases/` (les 3 dernières sont gardées), écrire sa version dans `CURRENT` par SFTP, puis redémarrer le pod. `.env` garde le `APP_RELEASE` plus récent jusqu'au prochain déploiement.

## 8. Sauvegardes

`backup.yml` tourne chaque nuit à 02:30 UTC (et à la main), pour `staging` et `production` :

1. `pg_dump -Fc` avec le client PostgreSQL 17 (image `postgres:17-alpine` sur le runner) contre le pod de base de données ;
2. envoi vers `s3://<bucket>/<environnement>/tierlist-<environnement>-<date>.dump` (Scaleway, `aws s3` avec `--endpoint-url`) ;
3. suppression des dumps plus vieux que `BACKUP_RETENTION_DAYS` (14 jours en production, 3 en staging).

Un environnement sans `BACKUP_POSTGRES_HOST` est sauté. Limites : la base doit être joignable depuis GitHub (mot de passe robuste, TLS si le pod le propose), une exécution planifiée peut démarrer en retard, et les identifiants de la base sont stockés dans GitHub.

Restauration (d'abord sur le staging) :

```bash
aws s3 cp --endpoint-url https://s3.fr-par.scw.cloud s3://<bucket>/staging/<dump> backup.dump
docker run --rm -i -e PGPASSWORD postgres:17-alpine \
  pg_restore --clean --if-exists --no-owner -h <hôte> -p <port> -U <utilisateur> -d <base> < backup.dump
```

## 9. Ce qui reste manuel

- Créer les pods, le tunnel, les enregistrements DNS et les ressources Scaleway (#159, #163).
- Les environnements, secrets et variables GitHub (§4), et le relecteur de `production`.
- Le redémarrage du pod, tant que `PANEL_SERVER_ID` et `PANEL_API_KEY` ne sont pas définis, ou quand le panel le refuse (en place sur le staging : le redémarrage y est automatique).
- Redéployer après le changement d'un secret ou d'une variable (§5.8).
- Approuver chaque déploiement en production.
- Tester une restauration (#162), puis après chaque montée de version majeure de PostgreSQL.

## 10. Essayer l'organisation de production en local

```bash
cd frontend && pnpm build && cd ..
bash deploy/build_bundle.sh local bundle     # bundle/tierlist-local.tar.gz
```

L'extraire, ajouter un `.env` (avec `TRUSTED_PROXY_IPS=127.0.0.1`), puis `bash start.sh` dans le dossier extrait : le frontend, l'API et le WebSocket répondent sur le port 8000. Ou, depuis `backend/`, copier `frontend/dist` vers `frontend_dist/` à la racine du dépôt et lancer `uv run uvicorn app.main:app`.

## 11. Historique

Le spike #155 avait choisi deux VPS avec Docker Compose et Caddy (TLS, `/api` retiré avant le backend). Ce design a été remplacé par les pods MineStrator avant d'être construit : les issues #158 à #163 ont été réécrites en conséquence.
