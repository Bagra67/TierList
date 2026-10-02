# TierList

Application TierList composée de deux projets dans un seul dépôt git :

| Dossier | Contenu | Outils |
| --- | --- | --- |
| [`backend/`](backend/README.md) | API **FastAPI** (Python 3.11+) | uv, Ruff, pytest |
| [`frontend/`](frontend/README.md) | **React + TypeScript** avec Vite, Redux Toolkit, Material UI | pnpm, ESLint, Prettier |

```
TierList/
├── backend/            # API FastAPI  → voir backend/README.md
├── frontend/           # App React    → voir frontend/README.md
│   └── .husky/         # Hook git pre-commit (pour tout le dépôt)
├── .vscode/            # Config VS Code partagée (format à l'enregistrement…)
└── README.md
```

---

## 1. Prérequis

| Outil | Installation | Vérification |
| --- | --- | --- |
| **uv** | Windows : `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"`<br>macOS/Linux : `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `uv --version` |
| **Node.js LTS** (20.19+) | Windows : `winget install OpenJS.NodeJS.LTS` — ou https://nodejs.org | `node --version` |
| **pnpm** | `npm install -g pnpm` | `pnpm --version` |
| **Git** | https://git-scm.com | `git --version` |

---

## 2. Installation (après un clone)

```bash
cd backend
uv sync           # crée backend/.venv et installe les dépendances Python

cd ../frontend
pnpm install      # installe les dépendances JS et active le hook git
```

---

## 3. Lancer l'application en développement

Ouvrez **deux terminaux** :

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

Plus de détails dans [backend/README.md](backend/README.md) et [frontend/README.md](frontend/README.md).

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
