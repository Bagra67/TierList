# TierList

[English](README.md) | Français

Application TierList composée de deux projets dans un seul dépôt git :

| Dossier                              | Contenu                                                  | Outils                                |
| ------------------------------------ | -------------------------------------------------------- | ------------------------------------- |
| [`backend/`](backend/README.fr.md)   | API **FastAPI** (Python 3.15+) + **PostgreSQL** (Docker) | uv, Ruff, pytest, SQLAlchemy, Alembic |
| [`frontend/`](frontend/README.fr.md) | **React + TypeScript** avec Vite                         | pnpm, ESLint, Prettier                |

Les docs de `docs/` et `TODO.md` sont en anglais uniquement. Le produit et comment on y joue : [docs/product/product.md](docs/product/product.md), avec ses [règles du jeu](docs/product/game-rules.md), ses [permissions](docs/product/permissions.md) et sa [roadmap](docs/product/roadmap.md). Organisation du code et emplacement du nouveau code : [docs/technical/architecture.md](docs/technical/architecture.md). Comptes et connexion : [docs/technical/authentication.md](docs/technical/authentication.md). Templates (modèle, API, purge) : [docs/technical/templates.md](docs/technical/templates.md). Marketplace (décision : recherche, tris, pagination par curseur) : [docs/technical/marketplace.md](docs/technical/marketplace.md). Temps réel des rooms (décision : WebSocket, reconnexion, timers, montée en charge) : [docs/technical/realtime.md](docs/technical/realtime.md). Images des tuiles (formats, compression, stockage S3, SeaweedFS, modération) : [docs/technical/images.md](docs/technical/images.md). Calcul des résultats (classement médian, votes absents, exemples chiffrés) : [docs/technical/results.md](docs/technical/results.md). Modération (journal de modération) : [docs/technical/moderation.md](docs/technical/moderation.md). Données de test pour le développement local et staging : [docs/technical/seed-data.md](docs/technical/seed-data.md). Traductions (français / anglais) : [docs/technical/i18n.md](docs/technical/i18n.md). Identité visuelle (couleurs, typographie, formes) : [docs/technical/visual-identity.md](docs/technical/visual-identity.md). Emails (SMTP, Mailpit) : [docs/technical/emails.md](docs/technical/emails.md). Suivi des erreurs (Sentry) : [docs/technical/monitoring.md](docs/technical/monitoring.md). Pages légales (politique de confidentialité) : [docs/technical/legal-pages.md](docs/technical/legal-pages.md). Versions et releases (`develop` → `main`) : [docs/technical/releasing.md](docs/technical/releasing.md), changements dans [CHANGELOG.fr.md](CHANGELOG.fr.md).

```
TierList/
├── backend/            # API FastAPI  → voir backend/README.fr.md
├── frontend/           # App React    → voir frontend/README.fr.md
│   └── .husky/         # Hook git pre-commit (pour tout le dépôt)
├── compose.yaml        # Base PostgreSQL, boîte Mailpit et stockage SeaweedFS de développement (Docker)
├── seaweedfs/          # Configuration de SeaweedFS (identités S3), développement et CI seulement
├── .github/            # Workflow CI, Dependabot, modèle de pull request
├── .claude/            # Configuration Claude Code partagée : hooks, skills, sous-agents, plugin
├── .mcp.json           # Serveurs MCP pour Claude Code : context7, playwright
├── .vscode/            # Config VS Code partagée (format à l'enregistrement, configurations de débogage…)
├── .editorconfig       # Encodage, fins de ligne, indentation pour tous les éditeurs
├── .nvmrc              # Version de Node.js (24)
├── dev.sh              # Lance backend + frontend en dev (Git Bash, macOS, Linux)
├── dev.cmd / dev.ps1   # Idem pour PowerShell / cmd
├── docs/
│   ├── product/        # Docs métier : produit, règles du jeu, permissions, roadmap
│   └── technical/      # Docs techniques : architecture, authentification, templates, images, temps réel, parties, résultats, guide des tests, i18n, emails, pages légales, releases, déploiement
├── TODO.md                    # Étapes manuelles restantes (déploiement, décisions)
└── README.md / README.fr.md   # Ce fichier (anglais / français)
```

---

## 1. Prérequis

| Outil                                       | Installation                                                                                                                                                                         | Vérification       |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------ |
| **uv**                                      | Windows : `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"`<br>macOS/Linux : `curl -LsSf https://astral.sh/uv/install.sh \| sh`                  | `uv --version`     |
| **Node.js 26 LTS** (version dans `.nvmrc`)  | Windows : `winget install OpenJS.NodeJS.LTS` — ou https://nodejs.org                                                                                                                 | `node --version`   |
| **pnpm**                                    | `npm install -g pnpm`                                                                                                                                                                | `pnpm --version`   |
| **Git**                                     | https://git-scm.com                                                                                                                                                                  | `git --version`    |
| **Docker Desktop**                          | Windows : `winget install -e --id Docker.DockerDesktop` (WSL2 requis, redémarrage possible), puis lancez Docker Desktop une fois — ou https://www.docker.com/products/docker-desktop | `docker info`      |
| **gitleaks** (exigé par le hook pre-commit) | Windows : `winget install -e --id Gitleaks.Gitleaks` (puis redémarrer VS Code et les terminaux)<br>macOS : `brew install gitleaks` — ou https://github.com/gitleaks/gitleaks         | `gitleaks version` |

---

## 2. Installation (après un clone)

```bash
cd backend
uv sync           # crée backend/.venv et installe les dépendances Python

cd ../frontend
pnpm install      # installe les dépendances JS et active le hook git

cd ..
cp backend/.env.example backend/.env   # puis changez le mot de passe dans backend/.env
```

`backend/.env` (non commité) contient les identifiants PostgreSQL : il est lu à la fois par le backend et par le conteneur Docker.

---

## 3. Lancer l'application en développement

### Base de données (PostgreSQL dans Docker)

Docker Desktop doit être lancé. Depuis la racine `TierList/` :

| Action                                         | Commande                                                                                                                                             |
| ---------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Démarrer la base (attend qu'elle soit prête)   | `docker compose up -d --wait`                                                                                                                        |
| Voir son état / ses logs                       | `docker compose ps` / `docker compose logs db`                                                                                                       |
| Lire les emails envoyés par le backend         | Mailpit : http://localhost:8025 ([docs/technical/emails.md](docs/technical/emails.md))                                                         |
| Parcourir les images envoyées                  | Filer SeaweedFS : http://localhost:8888/buckets/tierlist-images/ ([docs/technical/images.md](docs/technical/images.md#27-storage-and-serving)) |
| Arrêter (les données sont conservées)          | `docker compose down`                                                                                                                                |
| Tout réinitialiser (⚠️ **efface les données**) | `docker compose down -v`                                                                                                                             |

La base reste lancée en arrière-plan entre deux sessions de dev : pas besoin de la redémarrer à chaque fois. Vérifier que le backend y accède : http://127.0.0.1:8000/api/health/db → `{"status":"ok"}`.

### En une commande (recommandé)

Depuis la racine `TierList/`, selon votre terminal :

| Terminal                   | Commande    |
| -------------------------- | ----------- |
| **Git Bash**, macOS, Linux | `./dev.sh`  |
| PowerShell, cmd            | `.\dev.cmd` |

Lance le backend (http://127.0.0.1:8000) et le frontend (http://localhost:5173) dans le même terminal, avec rechargement automatique. **Ctrl+C arrête les deux.**

- Au premier lancement, le script installe automatiquement les dépendances si besoin (`uv sync`, `pnpm install`).
- Il démarre d'abord les services Docker, PostgreSQL, Mailpit et SeaweedFS (`docker compose up -d --wait`), et attend qu'ils soient prêts. Si Docker Desktop n'est pas lancé, il s'arrête avec un message clair. Pour démarrer sans eux : `./dev.sh --no-db` ou `.\dev.cmd -NoDb`.
- Dès que le backend et le frontend répondent, il ouvre le frontend, la doc de l'API (http://127.0.0.1:8000/api/docs), Mailpit (http://localhost:8025) et le filer SeaweedFS sur le bucket des images (http://localhost:8888, ces deux-là pas avec `--no-db`) dans le navigateur par défaut. Pour ne pas les ouvrir : `./dev.sh --no-open` ou `.\dev.cmd -NoOpen`.
- Si l'un des deux serveurs s'arrête (erreur, crash…), l'autre est arrêté aussi.
- Si le port 8000 ou 5173 est déjà occupé, `dev.sh` refuse de démarrer et vous l'indique.
- Dans `dev.sh`, les logs sont préfixés `[backend]` / `[frontend]`.

> ⚠️ Dans **Git Bash**, utilisez `dev.sh` et non `dev.cmd` : Git Bash ne transmet pas correctement Ctrl+C aux scripts Windows, et des serveurs pourraient rester actifs en arrière-plan.
> `.\dev.ps1` fonctionne aussi dans PowerShell si l'exécution de scripts est autorisée ; `dev.cmd` la contourne pour vous.

### Séparément, dans deux terminaux

**Terminal 1 — backend** (http://127.0.0.1:8000, docs sur `/api/docs`)

```bash
cd backend
uv run fastapi dev app/main.py
```

**Terminal 2 — frontend** (http://localhost:5173)

```bash
cd frontend
pnpm dev
```

Le frontend appelle le backend via `/api/...` (proxy Vite → port 8000, qui sert son API sous `/api` comme en production) : pas besoin de configurer CORS. Déploiement : [guide du déploiement](docs/technical/deployment.md).

---

## 4. Qualité du code (automatique)

**Dans VS Code** : à l'ouverture du dossier `TierList`, acceptez l'installation des extensions recommandées (ESLint, Prettier, Ruff, Python, Python Debugger, Docker). Le code est alors corrigé et formaté **à chaque enregistrement** :

- `.ts` / `.tsx` / `.json` / `.css` → Prettier + ESLint
- `.py` → Ruff

**Déboguer dans VS Code** (`.vscode/launch.json`, vue **Exécuter et déboguer**, puis F5) :

- **Backend: FastAPI** lance uvicorn sur le port 8000 sous le débogueur : les points d'arrêt dans `backend/app/` arrêtent la requête. Pas de rechargement automatique dans ce mode ; arrêtez `dev.sh` avant, le port est le même.
- **Frontend: Vitest (current file)** lance les tests du fichier de test ouvert, avec points d'arrêt dans les tests et dans `frontend/src/`.

**Avant chaque commit**, le hook git `frontend/.husky/pre-commit` lance :

1. `gitleaks` sur les modifications indexées : le commit est refusé si elles contiennent un secret (clé, mot de passe, token). La sortie indique le fichier, la ligne et la règle, avec le secret masqué. Un faux positif s'ignore avec un commentaire `gitleaks:allow` sur la ligne ;
2. `lint-staged` sur les fichiers du frontend modifiés (ESLint `--fix` + Prettier) ;
3. `ruff check` et `ruff format --check` sur le backend.

Si une erreur ne peut pas être corrigée automatiquement, le commit est bloqué : corrigez-la puis recommitez.

**Les messages de commit** sont vérifiés par le hook `frontend/.husky/commit-msg` (commitlint, `frontend/commitlint.config.js`) : ils doivent suivre Conventional Commits, `type(scope): résumé` (ex. `feat(backend): add the tier list API`), avec un résumé en minuscules et des lignes de corps de 100 caractères au plus. Types autorisés : `build`, `chore`, `ci`, `docs`, `feat`, `fix`, `perf`, `refactor`, `revert`, `style`, `test`.

Commandes manuelles :

|                       | Backend (`cd backend`)      | Frontend (`cd frontend`) |
| --------------------- | --------------------------- | ------------------------ |
| Lint                  | `uv run ruff check .`       | `pnpm lint`              |
| Corriger              | `uv run ruff check . --fix` | `pnpm lint:fix`          |
| Formater              | `uv run ruff format .`      | `pnpm format`            |
| Types                 | `uv run pyright`            | `pnpm typecheck`         |
| Code inutilisé        | —                           | `pnpm knip`              |
| Tests                 | `uv run pytest`             | `pnpm test`              |
| Tests + couverture    | `uv run pytest --cov=app`   | `pnpm test:coverage`     |
| Tests de bout en bout | —                           | `pnpm test:e2e`          |

Les tests d'intégration du backend ont besoin de la base, et de SeaweedFS pour les tests du stockage des images : `docker compose up -d --wait` (sinon ils sont ignorés en local). Les tests de bout en bout (Playwright) lancent la vraie application dans Chromium, Firefox et WebKit : ils ont besoin des mêmes services, des navigateurs (`pnpm exec playwright install chromium firefox webkit`, une fois) et du build du frontend (`pnpm build`). Fonctionnement des tests (outils, mise en place commune, commandes) : [docs/technical/testing.md](docs/technical/testing.md).

### Intégration continue (GitHub Actions)

`.github/workflows/ci.yml` tourne sur chaque pull request (y compris les PR empilées sur une autre branche de travail) et chaque push sur `develop` et `main` (enchaînement des workflows, choix pour la vitesse et comment garder la CI rapide : [docs/technical/ci.md](docs/technical/ci.md)) :

| Job          | Étapes                                                                                                                                                                                  |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Backend**  | `uv sync --locked`, Ruff (lint + format), Pyright, pytest avec couverture sur un service PostgreSQL 18 et le SeaweedFS de `compose.yaml`, en Python 3.15 (celui des pods de production) |
| **Frontend** | `pnpm install --frozen-lockfile`, ESLint, Prettier, `tsc`, knip, Vitest avec couverture, build de production                                                                            |
| **Secrets**  | gitleaks sur chaque commit de la PR (ou du push)                                                                                                                                        |
| **E2E**      | un job par navigateur (Chromium, Firefox, WebKit) : PostgreSQL, Mailpit et SeaweedFS, build du frontend, tests Playwright `pnpm test:e2e --project=<navigateur>`                        |

`.github/workflows/docs.yml` lance le job **Docs** sur les mêmes événements : chaque README (et le CHANGELOG) a sa version anglaise et française avec leur sélecteur de langue et, sur une PR, les deux versions changent ensemble. Les autres docs sont en anglais uniquement. Pour une exception justifiée (par ex. une coquille corrigée dans une seule langue d'un README), ajouter le label `skip-docs-sync` à la PR et expliquer pourquoi. Voir [docs/technical/testing.md](docs/technical/testing.md#5-ci-script-tests-githubscripts).

- Le résumé de l'exécution affiche un **rapport de tests** pour chaque job (résultat et durée de chaque test, détail des échecs, raisons des tests ignorés, tests les plus lents) et la couverture (sans seuil bloquant). Les rapports bruts sont conservés comme artefacts pendant 14 jours. Voir [docs/technical/testing.md](docs/technical/testing.md#31-test-report-on-ci).
- Les quatre jobs (`Backend`, `Frontend`, `Secrets`, `Docs`) sont des **contrôles requis** sur `develop` et `main` : une PR ne peut pas être fusionnée tant que la CI échoue. Les jobs `E2E` ne sont pas encore requis (voir le TODO).
- Sur une PR, `Backend` et `Frontend` ne tournent que si la PR touche leur partie (job `Changed parts`) : `frontend/` et `docs/` (vérifié par Prettier) pour Frontend, `backend/` pour Backend, les deux pour `backend/openapi.json` et pour tout autre fichier sauf le Markdown. `E2E` tourne dès que l'un des deux tourne. Un job sauté compte comme réussi. Un push sur `develop` ou `main` lance toujours tout, puisqu'il déploie ou publie une version.
- **Dependabot** (`.github/dependabot.yml`) ouvre chaque semaine des PR de mise à jour vers `develop` pour uv, pnpm, GitHub Actions et l'image Docker.
- Les nouvelles PR sont pré-remplies par `.github/pull_request_template.md`.

### Claude Code

La configuration Claude Code de `.claude/settings.json` est partagée avec toute l'équipe (`.claude/settings.local.json` reste personnel). Ses instructions pour les agents sont en anglais seulement, comme `AGENTS.md`.

- **Hooks** (`.claude/hooks/`, demandent Node.js, uv et les dépendances du frontend) :
  - après chaque modification d'un fichier par Claude, il est corrigé et formaté comme à l'enregistrement : Ruff pour `backend/**/*.py`, ESLint + Prettier pour les scripts du frontend, Prettier pour le JSON, le CSS, le Markdown et le HTML du frontend et de `docs/`. Une erreur impossible à corriger automatiquement est renvoyée à Claude ;
  - Claude ne peut pas modifier les fichiers `.env` (seulement `.env.example`), `uv.lock`, `pnpm-lock.yaml` ni les fichiers d'API générés `backend/openapi.json` et `frontend/src/api/schema.d.ts` ;
  - des rappels de suivre `AGENTS.md` au démarrage de la session, à chaque message et avant chaque modification.
- **Skills** (`.claude/skills/`) : `/api-sync` régénère `openapi.json` et les types d'API du frontend après un changement de contrat ; `/ship-check` lance en local les vérifications de la CI et la checklist de relecture d'`AGENTS.md`, puis en donne les résultats ; `/dependabot-review [PR...]` résume en français le changelog, les risques et l'état de la CI des PR Dependabot (toutes celles ouvertes par défaut).
- **Sous-agents** (`.claude/agents/`, en lecture seule) : `security-reviewer` (autorisations, sessions, envois d'images, salons, modération) et `i18n-docs-reviewer` (traductions, docs bilingues, guide des tests, politique de confidentialité, jeu de données).
- **Plugin** : `claude-code-setup` (annuaire Anthropic) recommande d'autres automatisations pour le projet ; demander à Claude des « recommandations d'automatisation ».
- **Serveurs MCP** (`.mcp.json`, à approuver une fois par chaque développeur au démarrage de Claude Code) :
  - `context7` : documentation des versions des librairies du projet, lue avant d'utiliser une API que le code n'utilise pas encore ;
  - `playwright` : pilote Chrome (profil en mémoire) sur l'app locale uniquement (`127.0.0.1:5173`, SeaweedFS, Mailpit), pour vérifier un changement du frontend dans un vrai navigateur, aussi depuis `/ship-check`. Il demande les dépendances du frontend et Chrome (sinon `npx playwright install chrome`).

---

## 5. Ajouter un package

|                   | Backend (`cd backend`)   | Frontend (`cd frontend`) |
| ----------------- | ------------------------ | ------------------------ |
| Dépendance        | `uv add <package>`       | `pnpm add <package>`     |
| Dépendance de dev | `uv add --dev <package>` | `pnpm add -D <package>`  |
| Supprimer         | `uv remove <package>`    | `pnpm remove <package>`  |

Plus de détails dans [backend/README.fr.md](backend/README.fr.md) et [frontend/README.fr.md](frontend/README.fr.md).

---

## 6. Git

- Un seul dépôt pour tout le projet, branche principale `main`.
- Commitez les fichiers de verrouillage (`backend/uv.lock`, `frontend/pnpm-lock.yaml`).
- `.venv/`, `node_modules/` et `dist/` sont ignorés.
- Après un `git pull` : `uv sync` dans `backend/` et `pnpm install` dans `frontend/` si les dépendances ont changé.
- Pour publier sur GitHub : créez un dépôt vide, puis
  ```bash
  git remote add origin https://github.com/<utilisateur>/TierList.git
  git push -u origin main
  ```

---

## 7. Licence

Code propriétaire, **tous droits réservés** : aucune réutilisation, copie, modification ni redistribution sans autorisation écrite de l'auteur. Voir [LICENSE](LICENSE).
