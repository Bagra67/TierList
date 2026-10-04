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

| Couche                 | Où                                                                                     | Responsabilité                                                                                                                                                                                                                                                                                                                                         |
| ---------------------- | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Composants             | `App.tsx` (routes, react-router), `pages/`, `components/`, `auth/`                     | Affichage et interaction uniquement. Lisent les données serveur via un hook ; n'appellent jamais `fetch` ni `useEffect` pour charger des données.                                                                                                                                                                                                      |
| Hooks                  | `api/<ressource>.ts` (`useCurrentUser`)                                                | Un hook TanStack Query par lecture (`useQuery`) ou écriture (`useMutation`) ; `queryKey` nomme la donnée en cache.                                                                                                                                                                                                                                     |
| Fonctions d'API        | `api/<ressource>.ts` (`getMe`)                                                         | Une fonction par endpoint, via `apiClient` ; lèvent `ApiError` en cas d'échec.                                                                                                                                                                                                                                                                         |
| Client HTTP            | `api/client.ts`                                                                        | `apiClient` (openapi-fetch, URL de base `/api`, typé par `schema.d.ts`), access token en mémoire et middleware de rafraîchissement.                                                                                                                                                                                                                    |
| Erreurs                | `errors/apiError.ts`, `errors/googleError.ts`                                          | `ApiError` (`status`, `body`, `code`, `params`, `detail` du backend comme `message`), `getFieldErrors` (erreurs 422 par champ), et `translateError` / `translateFieldError` / `translateGoogleError` (code d'erreur → message traduit).                                                                                                                |
| Composants d'interface | `components/ui/` (shadcn/ui), `index.css`                                              | Composants génériques générés par shadcn/ui (primitives Radix, classes Tailwind CSS v4) : ils appartiennent au projet et se modifient. Les composants métier restent dans `components/`. Thème (couleurs, arrondis, police) dans `index.css`. Voir le [README du frontend, Composants d'interface](../frontend/README.fr.md#10-composants-dinterface). |
| Traductions            | `i18n/` (`locales/fr.ts`, `locales/en.ts`), `components/LanguageSwitcher.tsx`          | Tout texte affiché passe par `t()` (react-i18next) ; le français est la référence, l'anglais doit avoir les mêmes clés. Voir le [guide i18n](i18n.fr.md).                                                                                                                                                                                              |
| Thème                  | `theme/`, `constants/theme.ts`, `components/ThemeSwitcher.tsx`, script de `index.html` | Préférence clair / sombre / système mémorisée dans le navigateur ; la classe `dark` sur `<html>` bascule les couleurs de `index.css`. Voir le [README du frontend, Mode sombre](../frontend/README.fr.md#mode-sombre).                                                                                                                                 |
| Constantes             | `constants/`                                                                           | Valeurs fixes : routes, statuts HTTP, limites et chemins d'auth, langues gérées, thèmes. Aucun littéral dans les composants ni les fonctions d'API ; les textes affichés sont des traductions, pas des constantes.                                                                                                                                     |
| Client de requêtes     | `api/queryClient.ts`                                                                   | Politique de nouvel essai et journalisation des requêtes en échec, à un seul endroit.                                                                                                                                                                                                                                                                  |
| Types d'API            | `api/schema.d.ts`                                                                      | Générés par `pnpm gen:api` ; jamais modifiés à la main.                                                                                                                                                                                                                                                                                                |

Détails et modèle pour un nouvel endpoint : [README frontend, Récupération des données](../frontend/README.fr.md#8-récupération-des-données).

## Backend (`backend/app/`)

| Couche         | Où aujourd'hui                                                                                                    | Responsabilité                                                                                                                                                                            |
| -------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Routes         | `api/routes/auth.py`, `main.py` (santé)                                                                           | HTTP uniquement : lire la requête, appeler un service, traduire les erreurs prévues en `AppHTTPException` (avec un `ErrorCode`), renvoyer un modèle de réponse Pydantic.                  |
| Schémas        | `schemas/auth.py`, `main.py` (`HealthResponse`), `core/errors.py` (`ErrorResponse`)                               | Contrats de requête et de réponse explicites (Pydantic). Ne jamais renvoyer directement un modèle ORM.                                                                                    |
| Services       | `services/auth.py`, `services/email.py`                                                                           | Règles métier et orchestration ; portent les frontières de transaction.                                                                                                                   |
| Repositories   | `repositories/users.py`, `repositories/refresh_tokens.py`                                                         | Requêtes en base (SQLAlchemy), sans règle métier.                                                                                                                                         |
| Modèles        | `db/base.py` (`Base`), `models/user.py`                                                                           | Modèles ORM ; leur metadata est la cible des migrations Alembic.                                                                                                                          |
| Infrastructure | `core/config.py`, `core/logging.py`, `core/errors.py`, `core/security.py`, `db/session.py`, `api/dependencies.py` | Configuration depuis `.env`, logs, format d'erreur, primitives de mots de passe et de tokens, moteur et session (dépendance `get_db_session`), dépendances communes (`get_current_user`). |
| Constantes     | `constants/` (`auth.py`, `google.py`, `error_codes.py`, `messages.py`, `logging.py`)                              | Valeurs fixes : noms de cookies, types de tokens, longueurs liées au schéma, URL de Google, codes d'erreur de l'API, messages de l'API pour les développeurs.                             |
| Exceptions     | `exceptions/` (`auth.py`, `google.py`, `http.py`)                                                                 | Exceptions du domaine, levées par les services et traduites en réponses HTTP par les routes ; `AppHTTPException`, l'erreur HTTP qui porte un `ErrorCode`.                                 |

### Structure

Depuis la première vraie ressource (l'authentification), le backend suit AGENTS.md §10 ; `main.py` contient encore les routes de santé :

```
backend/app/
├── api/routes/<ressource>.py   # routes (APIRouter), incluses par main.py
├── schemas/<ressource>.py      # modèles Pydantic de requête / réponse
├── services/<ressource>.py     # logique métier
├── repositories/<ressource>.py # accès à la base
├── models/<ressource>.py       # modèles SQLAlchemy (sous-classes de db.base.Base)
├── constants/                  # valeurs fixes (noms, limites, URL, messages de l'API)
├── exceptions/                 # exceptions du domaine
├── core/                       # config, logs, erreurs, sécurité
├── db/                         # inchangé : Base, moteur, session
└── main.py                     # création de l'app, handlers d'erreur, routers
```

Chaque nouveau modèle s'accompagne d'une migration Alembic (`uv run alembic revision --autogenerate -m "description"`), relue avant le commit.

## Conventions transverses

- **Contrat d'API** : après avoir modifié une route ou un schéma, lancer `uv run python scripts/export_openapi.py` (backend) puis `pnpm gen:api` (frontend), et commiter les deux fichiers. Un test et une étape CI vérifient qu'ils sont à jour.
- **Erreurs** : toute réponse d'erreur est une `ErrorResponse` (`{"detail": ..., "code": ..., "params"?: {...}, "errors"?: [...]}`). `code` est un code d'erreur stable que le frontend traduit ; `detail` est un texte anglais pour les développeurs. Lever `AppHTTPException` avec un `ErrorCode` pour les erreurs prévues ; les exceptions imprévues deviennent une 500 générique et journalisée. Voir [README backend, Format d'erreur](../backend/README.fr.md#12-format-derreur).
- **Sondes de santé** : `GET /health` (vie, sans dépendance) et `GET /health/db` (base joignable).
- **Authentification** : une route protégée dépend de `get_current_user` (`api/dependencies.py`), qui vérifie l'access token Bearer. Parcours, tokens et carte du code : [guide de l'authentification](authentication.fr.md).
- **Configuration** : variables d'environnement, lues depuis `backend/.env` par pydantic-settings (`core/config.py`) ; `backend/.env.example` les documente. Aucun secret dans le code (gitleaks vérifie chaque commit).
- **Constantes et réglages** : aucun nombre magique ni message en dur dans les routes, les services ou les composants.
  - Une valeur qui peut changer selon l'environnement (délai, timeout, règle de validation comme `PASSWORD_MIN_LENGTH`) est un **réglage** : un champ de `Settings` avec une valeur par défaut, documenté dans `backend/.env.example` et le README backend. On peut alors la changer sans pull request.
  - Une valeur fixe (nom de cookie, algorithme, URL de Google, longueur liée à une colonne de la base) est une **constante** de `constants/` (backend `app/constants/`, frontend `src/constants/`).
  - Les migrations Alembic gardent des valeurs en dur : une migration est un instantané du schéma et ne doit pas suivre une constante qui changerait plus tard.
- **Traductions** : aucun texte destiné à l'utilisateur en dur dans un composant, ni envoyé par le backend : l'API renvoie des codes d'erreur, le frontend les traduit. Chaque clé existe en français et en anglais. Règles : AGENTS.md §50 ; mode d'emploi : [guide i18n](i18n.fr.md).
- **Exceptions** : les exceptions du domaine vivent dans `app/exceptions/` (backend) et les classes d'erreur dans `src/errors/` (frontend), jamais dans les services, les routes ou les composants.
- **Logs** : `logging.getLogger(__name__)` dans `app/...`, niveau donné par `LOG_LEVEL`.
- **Tests** : backend dans `backend/tests/` (unitaires, plus `integration/` sur un vrai PostgreSQL), frontend à côté du code (`*.test.tsx`). Chaque test est décrit dans le [guide des tests](testing.fr.md).
- **Git** : Conventional Commits (vérifiés par commitlint), une branche et une PR fusionnée en squash par changement vers `develop` ; voir AGENTS.md §39–40.

## Décisions en attente

Volontairement repoussées (YAGNI), à trancher quand une fonctionnalité en aura besoin :

- **Images Docker de production et déploiement** : une fois la cible d'hébergement choisie.

Décidés depuis : l'authentification (access token JWT + refresh token rotatif, voir le [guide de l'authentification](authentication.fr.md)), le routage front (react-router) et la bibliothèque d'interface (Tailwind CSS v4 + shadcn/ui).
