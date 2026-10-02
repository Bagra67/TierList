# TierList — Backend FastAPI

Backend Python basé sur [FastAPI](https://fastapi.tiangolo.com/), géré avec le gestionnaire de paquets et de projets [uv](https://docs.astral.sh/uv/).

> Ce dossier fait partie du dépôt [TierList](../README.md). **Toutes les commandes ci-dessous se lancent depuis le dossier `backend/`** (`cd backend`).

---

## 1. Prérequis

- **uv** (il installe et gère lui-même Python si besoin)
- Python **3.11+** (version fixée dans `.python-version`)

### Installer uv

**Windows (PowerShell)** :
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS / Linux** :
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Redémarrez ensuite votre terminal, puis vérifiez :
```bash
uv --version
```

---

## 2. Installer le projet

Depuis le dossier `backend/` :
```bash
uv sync
```

Cette commande :
- crée l'environnement virtuel `.venv/` s'il n'existe pas ;
- installe toutes les dépendances (y compris celles de dev) exactement aux versions du fichier `uv.lock`.

### Activer l'environnement virtuel (optionnel)

Avec `uv run`, l'activation n'est **pas nécessaire** : uv utilise automatiquement `.venv`.
Si vous voulez quand même l'activer (par ex. pour utiliser `python` ou `fastapi` directement) :

| Système | Commande |
|---|---|
| Windows (PowerShell) | `.venv\Scripts\Activate.ps1` |
| Windows (cmd) | `.venv\Scripts\activate.bat` |
| macOS / Linux | `source .venv/bin/activate` |

Pour le désactiver : `deactivate`.

> VS Code est déjà configuré (`.vscode/settings.json` à la racine) pour utiliser `backend/.venv`. Sinon : `Ctrl+Shift+P` → *Python: Select Interpreter*.

---

## 3. Lancer le serveur

**Mode développement** (rechargement automatique à chaque modification) :
```bash
uv run fastapi dev app/main.py
```

**Mode production** :
```bash
uv run fastapi run app/main.py
```

Changer le port / l'hôte :
```bash
uv run fastapi dev app/main.py --port 8080 --host 0.0.0.0
```

Une fois lancé :
- API : http://127.0.0.1:8000
- Documentation interactive (Swagger) : http://127.0.0.1:8000/docs
- Documentation ReDoc : http://127.0.0.1:8000/redoc

Le frontend appelle le backend via le proxy Vite : une requête vers `http://localhost:5173/api/health` est redirigée vers `http://127.0.0.1:8000/health`. Le backend doit donc tourner sur le port **8000** pendant le développement du frontend.

---

## 4. Gérer les packages

> ⚠️ N'utilisez pas `pip install` directement : passez toujours par `uv` pour que `pyproject.toml` et `uv.lock` restent à jour.

| Action | Commande |
|---|---|
| Ajouter un package | `uv add <package>` (ex : `uv add sqlalchemy`) |
| Ajouter une version précise | `uv add "sqlalchemy>=2.0"` |
| Ajouter un package de dev (tests, lint…) | `uv add --dev <package>` (ex : `uv add --dev ruff`) |
| Supprimer un package | `uv remove <package>` |
| Mettre à jour un package | `uv lock --upgrade-package <package>` puis `uv sync` |
| Mettre à jour tous les packages | `uv lock --upgrade` puis `uv sync` |
| Voir l'arbre des dépendances | `uv tree` |
| Lister les packages installés | `uv pip list` |
| Réinstaller depuis le lockfile | `uv sync` |
| Installer sans les dépendances de dev (prod) | `uv sync --no-dev` |

Exécuter n'importe quelle commande dans l'environnement du projet :
```bash
uv run python script.py
uv run <commande>
```

---

## 5. Tests

```bash
uv run pytest
```

Mode verbeux : `uv run pytest -v`

---

## 6. Lint et formatage (Ruff)

[Ruff](https://docs.astral.sh/ruff/) sert à la fois de linter et de formateur. Il est configuré dans `pyproject.toml` (section `[tool.ruff]`).

| Action | Commande |
|---|---|
| Analyser le code | `uv run ruff check .` |
| Corriger automatiquement | `uv run ruff check . --fix` |
| Formater le code | `uv run ruff format .` |
| Vérifier le formatage sans modifier (CI) | `uv run ruff format . --check` |

Le hook git `pre-commit` (voir le [README racine](../README.md)) lance automatiquement `ruff check` et `ruff format --check` avant chaque commit. Pour corriger avant de commiter :
```bash
uv run ruff check . --fix && uv run ruff format .
```

> Dans VS Code, installez l'extension **Ruff** (`charliermarsh.ruff`) pour avoir le lint et le formatage à l'enregistrement.

---

## 7. Structure du projet

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py            # Point d'entrée FastAPI (routes / et /health)
│   └── routers/
│       ├── __init__.py
│       └── items.py       # Exemple de routes CRUD /items
├── tests/
│   └── test_main.py       # Tests avec TestClient
├── .python-version        # Version de Python utilisée par uv
├── pyproject.toml         # Métadonnées + dépendances du projet
├── uv.lock                # Versions exactes verrouillées (à commiter)
└── README.md
```

### Ajouter un nouveau router

1. Créez `app/routers/mon_router.py` :
   ```python
   from fastapi import APIRouter

   router = APIRouter(prefix="/mon-router", tags=["mon-router"])


   @router.get("/")
   def lister():
       return []
   ```
2. Enregistrez-le dans `app/main.py` :
   ```python
   from app.routers import items, mon_router

   app.include_router(mon_router.router)
   ```

---

## 8. Bonnes pratiques

- **Commitez** `pyproject.toml`, `uv.lock` et `.python-version`.
- **Ne commitez pas** `.venv/` (déjà dans `.gitignore`).
- Après un `git pull`, lancez `uv sync` pour vous remettre à jour.
- Changer de version de Python : `uv python pin 3.12` puis `uv sync`.
