# TierList — Backend FastAPI

[English](README.md) | Français

Backend Python basé sur [FastAPI](https://fastapi.tiangolo.com/), géré avec le gestionnaire de paquets et de projets [uv](https://docs.astral.sh/uv/).

> Ce dossier fait partie du dépôt [TierList](../README.fr.md). **Toutes les commandes ci-dessous se lancent depuis le dossier `backend/`** (`cd backend`).

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

Le frontend appelle le backend via le proxy Vite : une requête vers `http://localhost:5173/api/hello` est redirigée vers `http://127.0.0.1:8000/hello`. Le backend doit donc tourner sur le port **8000** pendant le développement du frontend.

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

Mode verbeux : `uv run pytest -v` — avec la couverture : `uv run pytest --cov=app`

### Tests d'intégration (vrai PostgreSQL)

Les tests de `tests/integration/` (marqueur `integration`) tournent sur un vrai PostgreSQL :

- Lancez d'abord la base : `docker compose up -d --wait` (depuis la racine du dépôt).
- Ils utilisent une base dédiée `<POSTGRES_DB>_test` (ex. `tierlist_test`), créée automatiquement, avec les migrations Alembic appliquées : **les données de développement ne sont jamais touchées**.
- Chaque test s'exécute dans une transaction annulée à la fin.
- Si PostgreSQL est injoignable, ils sont **ignorés** en local, mais ils **échouent** en CI.

| Action | Commande |
|---|---|
| Tests unitaires seulement | `uv run pytest -m "not integration"` |
| Tests d'intégration seulement | `uv run pytest -m integration` |

---

## 6. Lint et formatage (Ruff)

[Ruff](https://docs.astral.sh/ruff/) sert à la fois de linter et de formateur. Il est configuré dans `pyproject.toml` (section `[tool.ruff]`).

| Action | Commande |
|---|---|
| Analyser le code | `uv run ruff check .` |
| Corriger automatiquement | `uv run ruff check . --fix` |
| Formater le code | `uv run ruff format .` |
| Vérifier le formatage sans modifier (CI) | `uv run ruff format . --check` |

Le hook git `pre-commit` (voir le [README racine](../README.fr.md)) lance automatiquement `ruff check` et `ruff format --check` avant chaque commit. Pour corriger avant de commiter :
```bash
uv run ruff check . --fix && uv run ruff format .
```

> Dans VS Code, installez l'extension **Ruff** (`charliermarsh.ruff`) pour avoir le lint et le formatage à l'enregistrement.

### Vérification des types (Pyright)

```bash
uv run pyright
```

Configuré dans `pyproject.toml` (`[tool.pyright]`, mode `standard`, sur `app/`, `tests/` et `migrations/`). Lancé aussi par la CI.

---

## 7. Structure du projet

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py            # Point d'entrée FastAPI (GET /hello, GET /health/db)
│   ├── core/
│   │   ├── config.py      # Configuration lue depuis .env (pydantic-settings)
│   │   └── logging.py     # Logs de l'application (LOG_LEVEL, format uvicorn)
│   └── db/
│       ├── base.py        # Classe Base des modèles SQLAlchemy
│       └── session.py     # Engine, session (dépendance FastAPI), ping de la base
├── migrations/            # Migrations Alembic (env.py, versions/)
├── tests/
│   ├── test_main.py       # Tests unitaires avec TestClient (sans base réelle)
│   └── integration/       # Tests sur un vrai PostgreSQL (base <POSTGRES_DB>_test)
├── .env.example           # Modèle de .env (identifiants PostgreSQL)
├── alembic.ini            # Configuration Alembic
├── .python-version        # Version de Python utilisée par uv
├── pyproject.toml         # Métadonnées + dépendances du projet
├── uv.lock                # Versions exactes verrouillées (à commiter)
└── README.md / README.fr.md   # Ce fichier (anglais / français)
```

---

## 8. Bonnes pratiques

- **Commitez** `pyproject.toml`, `uv.lock` et `.python-version`.
- **Ne commitez pas** `.venv/` (déjà dans `.gitignore`).
- Après un `git pull`, lancez `uv sync` pour vous remettre à jour.
- Changer de version de Python : `uv python pin 3.12` puis `uv sync`.
- **Ne commitez pas** `.env` : seul `.env.example` est versionné.

---

## 9. Base de données (PostgreSQL + SQLAlchemy + Alembic)

La base tourne dans Docker (`compose.yaml` à la racine du dépôt, voir le [README racine](../README.fr.md)). Le backend s'y connecte avec **SQLAlchemy 2** et le driver **psycopg 3**.

### Configuration

Copiez `.env.example` en `.env` (dans `backend/`) et adaptez les valeurs :

| Variable | Rôle | Défaut |
|---|---|---|
| `POSTGRES_USER` | Utilisateur | — (obligatoire) |
| `POSTGRES_PASSWORD` | Mot de passe | — (obligatoire) |
| `POSTGRES_DB` | Nom de la base | — (obligatoire) |
| `POSTGRES_HOST` | Hôte vu depuis le backend | `127.0.0.1` |
| `POSTGRES_PORT` | Port | `5432` |
| `LOG_LEVEL` | Niveau des logs de l'application : `DEBUG`, `INFO`, `WARNING`, `ERROR` ou `CRITICAL` (insensible à la casse) | `INFO` |

Ce même fichier est lu par le conteneur PostgreSQL : changer le mot de passe **après** la création du volume n'a pas d'effet sur une base existante (il faut alors `docker compose down -v`, qui efface les données).

### Vérifier la connexion

`GET /health/db` exécute `SELECT 1` : `200 {"status": "ok"}` si la base répond, sinon `503 {"detail": "Base de données indisponible"}` (l'erreur détaillée est dans les logs du backend).

### Migrations (Alembic)

| Action | Commande |
|---|---|
| Créer une migration à partir des modèles | `uv run alembic revision --autogenerate -m "description"` |
| Appliquer les migrations | `uv run alembic upgrade head` |
| Annuler la dernière migration | `uv run alembic downgrade -1` |
| Voir la version actuelle de la base | `uv run alembic current` |

Les modèles doivent hériter de `app.db.base.Base` et être importés par `migrations/env.py` pour être détectés par `--autogenerate`. **Relisez toujours** une migration générée avant de l'appliquer.

---

## 10. Logs

Les logs de l'application (loggers sous `app`, par ex. `logging.getLogger(__name__)` dans `app/...`) sont configurés par `app/core/logging.py` :

- écrits sur stderr au **même format qu'uvicorn**, avec en plus le nom du logger : `ERROR:    app.main - Échec de la connexion à la base de données` ;
- niveau réglé par `LOG_LEVEL` (dans `.env` ou l'environnement, `INFO` par défaut) ; une valeur invalide arrête l'application au démarrage avec une erreur claire ;
- les logs d'uvicorn gardent leur propre configuration : utilisez `--log-level` sur `fastapi dev` / `fastapi run` pour les régler.
