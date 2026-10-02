# Feuille de route : finaliser le starter TierList

[English](starter-roadmap.md) | Français

Ce document liste ce qui manque pour **initialiser** proprement le projet, avant de développer la première fonctionnalité. Il ne contient aucune fonctionnalité métier : seulement l'outillage, la qualité et l'organisation.

## État actuel

- **Backend** FastAPI : `GET /hello`, plus `GET /health/db`, relié à PostgreSQL (SQLAlchemy 2, psycopg 3, Alembic).
- **Base** PostgreSQL 18 dans Docker (`compose.yaml`).
- **Frontend** React + TypeScript (Vite) : affiche le « Hello World » renvoyé par le backend.
- **Logs** : logs de l'application configurés via `LOG_LEVEL`, au format d'uvicorn.
- **Erreurs** : format d'erreur JSON unique (`ErrorResponse`) pour les erreurs HTTP, de validation et imprévues ; lu par `ApiError` côté frontend.
- **Contrat d'API** : `backend/openapi.json` exporté et vérifié ; types d'API du frontend générés à partir de lui (`pnpm gen:api`).
- **Récupération des données** : TanStack Query au-dessus d'un client openapi-fetch commun, typé par le contrat d'API.
- **Outillage** : uv, pnpm, Ruff, Pyright, ESLint, Prettier (aussi sur `docs/`), hook husky pre-commit, scripts `dev.*` ; versions de Node et pnpm épinglées.
- **Tests** : pytest (unitaires + intégration sur un vrai PostgreSQL), Vitest + Testing Library, rapports de couverture.
- **CI** : GitHub Actions (jobs `Backend` et `Frontend`, requis sur `develop` et `main`), Dependabot, modèle de pull request ; les branches de travail mergées sont supprimées automatiquement.

Les points réalisés ont été retirés de cette liste ; les autres gardent leur numéro d'origine.

Chaque point ci-dessous indique ce qui manque, pourquoi c'est utile et ce qu'il faut faire. Il fera l'objet d'un commit séparé, avec la mise à jour du README concerné.

---

## P1 : indispensable avant la première fonctionnalité

Tous les points P1 sont réalisés.

## P2 : fortement recommandé

11. **Séparer les sondes de santé** : `/health` vérifie seulement que l'application répond, `/health/db` que la base est joignable. Docker ou un hébergeur utilise la première, le diagnostic la seconde.

12. **Démarrer la base avec les scripts dev** : `dev.sh` et `dev.ps1` lanceraient `docker compose up -d --wait` avant les serveurs. Le message serait clair si Docker n'est pas lancé, et une option permettrait de sauter cette étape.

## P3 : confort et hygiène

14. **`.editorconfig`** : LF, UTF-8 et indentation, pour les éditeurs autres que VS Code.

15. **VS Code** :
    - `launch.json` pour déboguer FastAPI et Vitest (il faut l'autoriser dans `.gitignore`) ;
    - ajouter l'extension Docker aux recommandations.

16. **Recherche de secrets** avant chaque commit, avec gitleaks dans le hook pre-commit, en complément du `.gitignore`.

<!-- 17 done: list restarts at 18 to keep the original numbers -->

18. **Documentation** :
    - un court `docs/architecture.md` : couches, flux front → API → service → repository → DB, conventions.

19. **Vérifier les messages de commit** : Conventional Commits est désormais la règle (AGENTS.md §39) ; commitlint dans husky la vérifierait automatiquement. C'est utile pour un changelog automatique. Optionnel.

## Volontairement non proposé (pour l'instant)

Ces points sont repoussés à plus tard (YAGNI) :

- **Dockerfiles de production et déploiement** : à faire quand une cible d'hébergement sera choisie.
- **Authentification, routage front (react-router), bibliothèque d'interface** : ce sont des choix liés aux fonctionnalités.
- **Réorganiser `main.py` en `api/routes/` et en services** : à faire avec la première vraie ressource, pas avant.

---

## Vérification de chaque point

- Backend : `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`.
- Frontend : `pnpm lint`, `pnpm format:check`, `pnpm typecheck`, `pnpm test`, `pnpm build`.
- Bout en bout : `docker compose up -d --wait`, puis `GET /health/db` doit renvoyer `{"status":"ok"}`.
- CI : pousser une branche et vérifier que les jobs passent (`gh run watch`).
