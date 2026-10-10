# TierList

[English](README.md) | Français

Application TierList composée de deux projets dans un seul dépôt git :

| Dossier                              | Contenu                                                  | Outils                                |
| ------------------------------------ | -------------------------------------------------------- | ------------------------------------- |
| [`backend/`](backend/README.fr.md)   | API **FastAPI** (Python 3.11+) + **PostgreSQL** (Docker) | uv, Ruff, pytest, SQLAlchemy, Alembic |
| [`frontend/`](frontend/README.fr.md) | **React + TypeScript** avec Vite                         | pnpm, ESLint, Prettier                |

Le produit et comment on y joue : [docs/product/product.fr.md](docs/product/product.fr.md), avec ses [règles du jeu](docs/product/game-rules.fr.md), ses [permissions](docs/product/permissions.fr.md) et sa [roadmap](docs/product/roadmap.fr.md). Organisation du code et emplacement du nouveau code : [docs/technical/architecture.fr.md](docs/technical/architecture.fr.md). Comptes et connexion : [docs/technical/authentication.fr.md](docs/technical/authentication.fr.md). Templates (modèle, API, purge) : [docs/technical/templates.fr.md](docs/technical/templates.fr.md). Traductions (français / anglais) : [docs/technical/i18n.fr.md](docs/technical/i18n.fr.md). Emails (SMTP, Mailpit) : [docs/technical/emails.fr.md](docs/technical/emails.fr.md). Versions et releases (`develop` → `main`) : [docs/technical/releasing.fr.md](docs/technical/releasing.fr.md), changements dans [CHANGELOG.fr.md](CHANGELOG.fr.md).

```
TierList/
├── backend/            # API FastAPI  → voir backend/README.fr.md
├── frontend/           # App React    → voir frontend/README.fr.md
│   └── .husky/         # Hook git pre-commit (pour tout le dépôt)
├── compose.yaml        # Base PostgreSQL et boîte Mailpit de développement (Docker)
├── .github/            # Workflow CI, Dependabot, modèle de pull request
├── .vscode/            # Config VS Code partagée (format à l'enregistrement, configurations de débogage…)
├── .editorconfig       # Encodage, fins de ligne, indentation pour tous les éditeurs
├── .nvmrc              # Version de Node.js (24)
├── dev.sh              # Lance backend + frontend en dev (Git Bash, macOS, Linux)
├── dev.cmd / dev.ps1   # Idem pour PowerShell / cmd
├── docs/
│   ├── product/        # Docs métier : produit, règles du jeu, permissions, roadmap
│   └── technical/      # Docs techniques : architecture, authentification, templates, guide des tests, i18n, emails, releases
├── TODO.md / TODO.fr.md       # Étapes manuelles restantes (déploiement, décisions)
└── README.md / README.fr.md   # Ce fichier (anglais / français)
```

---

## 1. Prérequis

| Outil                                       | Installation                                                                                                                                                                         | Vérification       |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------ |
| **uv**                                      | Windows : `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"`<br>macOS/Linux : `curl -LsSf https://astral.sh/uv/install.sh \| sh`                  | `uv --version`     |
| **Node.js 26** (version dans `.nvmrc`)      | Windows : `winget install OpenJS.NodeJS` — ou https://nodejs.org                                                                                                                     | `node --version`   |
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

| Action                                         | Commande                                                                 |
| ---------------------------------------------- | ------------------------------------------------------------------------ |
| Démarrer la base (attend qu'elle soit prête)   | `docker compose up -d --wait`                                            |
| Voir son état / ses logs                       | `docker compose ps` / `docker compose logs db`                           |
| Lire les emails envoyés par le backend         | Mailpit : http://localhost:8025 ([docs/technical/emails.fr.md](docs/technical/emails.fr.md)) |
| Arrêter (les données sont conservées)          | `docker compose down`                                                    |
| Tout réinitialiser (⚠️ **efface les données**) | `docker compose down -v`                                                 |

La base reste lancée en arrière-plan entre deux sessions de dev : pas besoin de la redémarrer à chaque fois. Vérifier que le backend y accède : http://127.0.0.1:8000/health/db → `{"status":"ok"}`.

### En une commande (recommandé)

Depuis la racine `TierList/`, selon votre terminal :

| Terminal                   | Commande    |
| -------------------------- | ----------- |
| **Git Bash**, macOS, Linux | `./dev.sh`  |
| PowerShell, cmd            | `.\dev.cmd` |

Lance le backend (http://127.0.0.1:8000) et le frontend (http://localhost:5173) dans le même terminal, avec rechargement automatique. **Ctrl+C arrête les deux.**

- Au premier lancement, le script installe automatiquement les dépendances si besoin (`uv sync`, `pnpm install`).
- Il démarre d'abord la base PostgreSQL (`docker compose up -d --wait`) et attend qu'elle soit prête. Si Docker Desktop n'est pas lancé, il s'arrête avec un message clair. Pour démarrer sans la base : `./dev.sh --no-db` ou `.\dev.cmd -NoDb`.
- Si l'un des deux serveurs s'arrête (erreur, crash…), l'autre est arrêté aussi.
- Si le port 8000 ou 5173 est déjà occupé, `dev.sh` refuse de démarrer et vous l'indique.
- Dans `dev.sh`, les logs sont préfixés `[backend]` / `[frontend]`.

> ⚠️ Dans **Git Bash**, utilisez `dev.sh` et non `dev.cmd` : Git Bash ne transmet pas correctement Ctrl+C aux scripts Windows, et des serveurs pourraient rester actifs en arrière-plan.
> `.\dev.ps1` fonctionne aussi dans PowerShell si l'exécution de scripts est autorisée ; `dev.cmd` la contourne pour vous.

### Séparément, dans deux terminaux

**Terminal 1 — backend** (http://127.0.0.1:8000, docs sur `/docs`)

```bash
cd backend
uv run fastapi dev app/main.py
```

**Terminal 2 — frontend** (http://localhost:5173)

```bash
cd frontend
pnpm dev
```

Le frontend appelle le backend via `/api/...` (proxy Vite → port 8000) : pas besoin de configurer CORS en développement.

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

|                    | Backend (`cd backend`)      | Frontend (`cd frontend`) |
| ------------------ | --------------------------- | ------------------------ |
| Lint               | `uv run ruff check .`       | `pnpm lint`              |
| Corriger           | `uv run ruff check . --fix` | `pnpm lint:fix`          |
| Formater           | `uv run ruff format .`      | `pnpm format`            |
| Types              | `uv run pyright`            | `pnpm typecheck`         |
| Code inutilisé     | —                           | `pnpm knip`              |
| Tests              | `uv run pytest`             | `pnpm test`              |
| Tests + couverture | `uv run pytest --cov=app`   | `pnpm test:coverage`     |

Les tests d'intégration du backend ont besoin de la base : `docker compose up -d --wait` (sinon ils sont ignorés en local). Fonctionnement et but de chaque test : [docs/technical/testing.fr.md](docs/technical/testing.fr.md).

### Intégration continue (GitHub Actions)

`.github/workflows/ci.yml` tourne sur chaque pull request (y compris les PR empilées sur une autre branche de travail) et chaque push sur `develop` et `main` :

| Job          | Étapes                                                                                                       |
| ------------ | ------------------------------------------------------------------------------------------------------------ |
| **Backend**  | `uv sync --locked`, Ruff (lint + format), Pyright, pytest avec couverture sur un service PostgreSQL 18       |
| **Frontend** | `pnpm install --frozen-lockfile`, ESLint, Prettier, `tsc`, knip, Vitest avec couverture, build de production |
| **Secrets**  | gitleaks sur chaque commit de la PR (ou du push)                                                             |

`.github/workflows/docs.yml` lance le job **Docs** sur les mêmes événements : chaque doc a sa version anglaise et française avec leur sélecteur de langue et, sur une PR, les deux versions changent ensemble et un test modifié est accompagné des deux guides des tests (`docs/technical/testing.md` + `docs/technical/testing.fr.md`). Pour une exception justifiée (par ex. une coquille corrigée dans une seule langue), ajouter le label `skip-docs-sync` à la PR et expliquer pourquoi. Voir [docs/technical/testing.fr.md](docs/technical/testing.fr.md#5-tests-des-scripts-de-ci-githubscripts).

- Le résumé de l'exécution affiche un **rapport de tests** pour chaque job (résultat et durée de chaque test, détail des échecs, raisons des tests ignorés, tests les plus lents) et la couverture (sans seuil bloquant). Les rapports bruts sont conservés comme artefacts pendant 14 jours. Voir [docs/technical/testing.fr.md](docs/technical/testing.fr.md#31-rapport-de-tests-en-ci).
- Les quatre jobs (`Backend`, `Frontend`, `Secrets`, `Docs`) sont des **contrôles requis** sur `develop` et `main` : une PR ne peut pas être fusionnée tant que la CI échoue.
- **Dependabot** (`.github/dependabot.yml`) ouvre chaque semaine des PR de mise à jour vers `develop` pour uv, pnpm, GitHub Actions et l'image Docker.
- Les nouvelles PR sont pré-remplies par `.github/pull_request_template.md`.

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
