# Architecture

[English](architecture.md) | Français

Comment le code de TierList est organisé, et où placer le nouveau code. Les règles d'ingénierie elles-mêmes sont dans [AGENTS.md](../AGENTS.md) ; cette page décrit comment elles s'appliquent aujourd'hui à ce dépôt.

## Vue d'ensemble

```
Navigateur
  │
  ▼
Composant React ──► hook useX() ──► getX() ──► apiClient ──► /api/...   (frontend, Vite)
                    TanStack Query              openapi-fetch       │
                                                                    │ proxy Vite (dev) : /api/x → :8000/x
                                                                    ▼
Route FastAPI ──► service ──► repository ──► session SQLAlchemy ──► PostgreSQL   (backend)
 (HTTP seul)     (métier)     (requêtes)      (app/db/session.py)     (Docker)
```

Le backend et le frontend ne communiquent que par HTTP. Le contrat entre eux est le schéma OpenAPI : `backend/openapi.json`, généré depuis les routes FastAPI et les modèles Pydantic, à partir duquel le frontend génère ses types TypeScript.

## Frontend (`frontend/src/`)

| Couche             | Où                                                                 | Responsabilité                                                                                                                                    |
| ------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Composants         | `App.tsx` (routes, react-router), `pages/`, `components/`, `auth/` | Affichage et interaction uniquement. Lisent les données serveur via un hook ; n'appellent jamais `fetch` ni `useEffect` pour charger des données. |
| Hooks              | `api/<ressource>.ts` (`useHello`)                                  | Un hook TanStack Query par lecture (`useQuery`) ou écriture (`useMutation`) ; `queryKey` nomme la donnée en cache.                                |
| Fonctions d'API    | `api/<ressource>.ts` (`getHello`)                                  | Une fonction par endpoint, via `apiClient` ; lèvent `ApiError` en cas d'échec.                                                                    |
| Client HTTP        | `api/client.ts`                                                    | `apiClient` (openapi-fetch, URL de base `/api`, typé par `schema.d.ts`) et `ApiError` (`status`, `body`, `detail` du backend comme `message`).    |
| Client de requêtes | `api/queryClient.ts`                                               | Politique de nouvel essai et journalisation des requêtes en échec, à un seul endroit.                                                             |
| Types d'API        | `api/schema.d.ts`                                                  | Générés par `pnpm gen:api` ; jamais modifiés à la main.                                                                                           |

Détails et modèle pour un nouvel endpoint : [README frontend, Récupération des données](../frontend/README.fr.md#8-récupération-des-données).

## Backend (`backend/app/`)

| Couche         | Où aujourd'hui                                                                                                    | Responsabilité                                                                                                                                                                            |
| -------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Routes         | `api/routes/auth.py`, `main.py` (hello, santé)                                                                    | HTTP uniquement : lire la requête, appeler un service, traduire les erreurs prévues en `HTTPException`, renvoyer un modèle de réponse Pydantic.                                           |
| Schémas        | `schemas/auth.py`, `main.py` (`HelloResponse`, `HealthResponse`), `core/errors.py` (`ErrorResponse`)              | Contrats de requête et de réponse explicites (Pydantic). Ne jamais renvoyer directement un modèle ORM.                                                                                    |
| Services       | `services/auth.py`                                                                                                | Règles métier et orchestration ; portent les frontières de transaction.                                                                                                                   |
| Repositories   | `repositories/users.py`, `repositories/refresh_tokens.py`                                                         | Requêtes en base (SQLAlchemy), sans règle métier.                                                                                                                                         |
| Modèles        | `db/base.py` (`Base`), `models/user.py`                                                                           | Modèles ORM ; leur metadata est la cible des migrations Alembic.                                                                                                                          |
| Infrastructure | `core/config.py`, `core/logging.py`, `core/errors.py`, `core/security.py`, `db/session.py`, `api/dependencies.py` | Configuration depuis `.env`, logs, format d'erreur, primitives de mots de passe et de tokens, moteur et session (dépendance `get_db_session`), dépendances communes (`get_current_user`). |

### Structure

Depuis la première vraie ressource (l'authentification), le backend suit AGENTS.md §10 ; `main.py` contient encore les routes hello et santé :

```
backend/app/
├── api/routes/<ressource>.py   # routes (APIRouter), incluses par main.py
├── schemas/<ressource>.py      # modèles Pydantic de requête / réponse
├── services/<ressource>.py     # logique métier
├── repositories/<ressource>.py # accès à la base
├── models/<ressource>.py       # modèles SQLAlchemy (sous-classes de db.base.Base)
├── core/                       # inchangé : config, logs, erreurs
├── db/                         # inchangé : Base, moteur, session
└── main.py                     # création de l'app, handlers d'erreur, routers
```

Chaque nouveau modèle s'accompagne d'une migration Alembic (`uv run alembic revision --autogenerate -m "description"`), relue avant le commit.

## Conventions transverses

- **Contrat d'API** : après avoir modifié une route ou un schéma, lancer `uv run python scripts/export_openapi.py` (backend) puis `pnpm gen:api` (frontend), et commiter les deux fichiers. Un test et une étape CI vérifient qu'ils sont à jour.
- **Erreurs** : toute réponse d'erreur est une `ErrorResponse` (`{"detail": ..., "errors"?: [...]}`). Lever `HTTPException` pour les erreurs prévues ; les exceptions imprévues deviennent une 500 générique et journalisée. Voir [README backend, Format d'erreur](../backend/README.fr.md#12-format-derreur).
- **Sondes de santé** : `GET /health` (vie, sans dépendance) et `GET /health/db` (base joignable).
- **Authentification** : une route protégée dépend de `get_current_user` (`api/dependencies.py`), qui vérifie l'access token Bearer. Parcours, tokens et carte du code : [guide de l'authentification](authentication.fr.md).
- **Configuration** : variables d'environnement, lues depuis `backend/.env` par pydantic-settings (`core/config.py`) ; `backend/.env.example` les documente. Aucun secret dans le code (gitleaks vérifie chaque commit).
- **Logs** : `logging.getLogger(__name__)` dans `app/...`, niveau donné par `LOG_LEVEL`.
- **Tests** : backend dans `backend/tests/` (unitaires, plus `integration/` sur un vrai PostgreSQL), frontend à côté du code (`*.test.tsx`). Chaque test est décrit dans le [guide des tests](testing.fr.md).
- **Git** : Conventional Commits (vérifiés par commitlint), une branche et une PR fusionnée en squash par changement vers `develop` ; voir AGENTS.md §39–40.

## Décisions en attente

Volontairement repoussées (YAGNI), à trancher quand une fonctionnalité en aura besoin :

- **Images Docker de production et déploiement** : une fois la cible d'hébergement choisie.
- **Bibliothèque d'interface** : ce choix dépend des fonctionnalités.

Décidés depuis : l'authentification (access token JWT + refresh token rotatif, voir le [guide de l'authentification](authentication.fr.md)) et le routage front (react-router).
