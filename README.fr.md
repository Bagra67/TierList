# TierList

[English](README.md) | Français

Application TierList composée de deux projets dans un seul dépôt git :

| Dossier | Contenu | Outils |
| --- | --- | --- |
| [`backend/`](backend/README.fr.md) | API **FastAPI** (Python 3.11+) + **PostgreSQL** (Docker) | uv, Ruff, pytest, SQLAlchemy, Alembic |
| [`frontend/`](frontend/README.fr.md) | **React + TypeScript** avec Vite | pnpm, ESLint, Prettier |

```
TierList/
├── backend/            # API FastAPI  → voir backend/README.fr.md
├── frontend/           # App React    → voir frontend/README.fr.md
│   └── .husky/         # Hook git pre-commit (pour tout le dépôt)
├── compose.yaml        # Base PostgreSQL de développement (Docker)
├── .vscode/            # Config VS Code partagée (format à l'enregistrement…)
├── dev.sh              # Lance backend + frontend en dev (Git Bash, macOS, Linux)
├── dev.cmd / dev.ps1   # Idem pour PowerShell / cmd
├── docs/               # Documentation (feuille de route…)
└── README.md / README.fr.md   # Ce fichier (anglais / français)
```

---

## 1. Prérequis

| Outil | Installation | Vérification |
| --- | --- | --- |
| **uv** | Windows : `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"`<br>macOS/Linux : `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `uv --version` |
| **Node.js 24 LTS** (version dans `.nvmrc`) | Windows : `winget install OpenJS.NodeJS.LTS` — ou https://nodejs.org | `node --version` |
| **pnpm** | `npm install -g pnpm` | `pnpm --version` |
| **Git** | https://git-scm.com | `git --version` |
| **Docker Desktop** | Windows : `winget install -e --id Docker.DockerDesktop` (WSL2 requis, redémarrage possible), puis lancez Docker Desktop une fois — ou https://www.docker.com/products/docker-desktop | `docker info` |

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

| Action | Commande |
| --- | --- |
| Démarrer la base (attend qu'elle soit prête) | `docker compose up -d --wait` |
| Voir son état / ses logs | `docker compose ps` / `docker compose logs db` |
| Arrêter (les données sont conservées) | `docker compose down` |
| Tout réinitialiser (⚠️ **efface les données**) | `docker compose down -v` |

La base reste lancée en arrière-plan entre deux sessions de dev : pas besoin de la redémarrer à chaque fois. Vérifier que le backend y accède : http://127.0.0.1:8000/health/db → `{"status":"ok"}`.

### En une commande (recommandé)

Depuis la racine `TierList/`, selon votre terminal :

| Terminal | Commande |
| --- | --- |
| **Git Bash**, macOS, Linux | `./dev.sh` |
| PowerShell, cmd | `.\dev.cmd` |

Lance le backend (http://127.0.0.1:8000) et le frontend (http://localhost:5173) dans le même terminal, avec rechargement automatique. **Ctrl+C arrête les deux.**

- Au premier lancement, le script installe automatiquement les dépendances si besoin (`uv sync`, `pnpm install`).
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

Le frontend affiche le « Hello World » renvoyé par le backend. Il l'appelle via `/api/...` (proxy Vite → port 8000) : pas besoin de configurer CORS en développement.

---

## 4. Qualité du code (automatique)

**Dans VS Code** : à l'ouverture du dossier `TierList`, acceptez l'installation des extensions recommandées (ESLint, Prettier, Ruff, Python). Le code est alors corrigé et formaté **à chaque enregistrement** :
- `.ts` / `.tsx` / `.json` / `.css` → Prettier + ESLint
- `.py` → Ruff

**Avant chaque commit**, le hook git `frontend/.husky/pre-commit` lance :
1. `lint-staged` sur les fichiers du frontend modifiés (ESLint `--fix` + Prettier) ;
2. `ruff check` et `ruff format --check` sur le backend.

Si une erreur ne peut pas être corrigée automatiquement, le commit est bloqué : corrigez-la puis recommitez.

Commandes manuelles :

| | Backend (`cd backend`) | Frontend (`cd frontend`) |
| --- | --- | --- |
| Lint | `uv run ruff check .` | `pnpm lint` |
| Corriger | `uv run ruff check . --fix` | `pnpm lint:fix` |
| Formater | `uv run ruff format .` | `pnpm format` |
| Tests / types | `uv run pytest` | `pnpm typecheck` |

---

## 5. Ajouter un package

| | Backend (`cd backend`) | Frontend (`cd frontend`) |
| --- | --- | --- |
| Dépendance | `uv add <package>` | `pnpm add <package>` |
| Dépendance de dev | `uv add --dev <package>` | `pnpm add -D <package>` |
| Supprimer | `uv remove <package>` | `pnpm remove <package>` |

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
