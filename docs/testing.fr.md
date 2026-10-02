# Guide des tests

[English](testing.md) | Français

Ce guide explique le fonctionnement des tests de TierList : les outils utilisés, ce que fait chaque test, son but et le résultat attendu.

| | Backend | Frontend |
| --- | --- | --- |
| Outil de test | [pytest](https://docs.pytest.org/) | [Vitest](https://vitest.dev/) |
| Compléments | `TestClient` de FastAPI, fixtures pytest, pytest-cov | Testing Library, jsdom, jest-dom, couverture v8 |
| Emplacement | `backend/tests/` | à côté du code : `frontend/src/**/*.test.tsx` |
| Lancer | `uv run pytest` (dans `backend/`) | `pnpm test` (dans `frontend/`) |
| Couverture | `uv run pytest --cov=app` | `pnpm test:coverage` |

Les deux suites de tests tournent aussi sur **chaque pull request** dans la CI (`.github/workflows/ci.yml`). Une PR ne peut pas être fusionnée dans `develop` ou `main` tant qu'un test échoue.

---

## 1. Backend (pytest)

### 1.1 Fonctionnement de pytest

- **Découverte** : pytest cherche dans `tests/` (configuré dans `pyproject.toml`) les fichiers nommés `test_*.py`, et exécute chaque fonction nommée `test_*` qu'ils contiennent.
- **Assertions** : un test est une simple fonction qui utilise `assert`. Si un `assert` échoue ou si une exception est levée, le test **échoue**, et pytest affiche les valeurs comparées.
- **Fixtures** : une préparation réutilisable, passée au test via ses paramètres. Par exemple, `def test_x(client)` reçoit la fixture `client`. Une fixture peut exécuter du nettoyage après le test (la partie après `yield`). Sa *portée* (*scope*) indique à quelle fréquence elle est créée : à chaque test (par défaut) ou une seule fois par exécution (`scope="session"`).
- **Fixtures intégrées utilisées ici** :
  - `monkeypatch` modifie des variables d'environnement ou le dossier courant, pour un seul test ;
  - `tmp_path` fournit un dossier temporaire vide ;
  - `capsys` capture ce qui est écrit sur stdout/stderr.
- **Marqueurs** : des étiquettes sur les tests. `integration` marque les tests qui ont besoin d'un vrai PostgreSQL : on peut les sélectionner avec `-m integration` ou les exclure avec `-m "not integration"`.
- **`TestClient` de FastAPI** : envoie des requêtes HTTP à l'application **en mémoire**, sans démarrer de serveur. Par exemple, `client.get("/hello")` renvoie une réponse dont on vérifie le `status_code` et le `json()`.
- **`app.dependency_overrides`** : remplace une dépendance FastAPI pendant un test. Les tests remplacent `get_db_session`, la dépendance qui fournit la session de base de données, pour simuler une base qui fonctionne ou qui est en panne.

### 1.2 Lancer les tests

| Commande (dans `backend/`) | Effet |
| --- | --- |
| `uv run pytest` | Tous les tests |
| `uv run pytest -v` | Une ligne par test, avec son nom et son résultat |
| `uv run pytest -m "not integration"` | Tests unitaires seulement (pas besoin de base) |
| `uv run pytest -m integration` | Tests d'intégration seulement (base nécessaire) |
| `uv run pytest --cov=app` | Tous les tests, plus un tableau de couverture de `app/` |
| `uv run pytest tests/test_logging.py::test_log_level_defaults_to_info` | Un seul test |

Les tests d'intégration ont besoin que PostgreSQL tourne : `docker compose up -d --wait` depuis la racine du dépôt.

### 1.3 Tests unitaires : `tests/test_main.py` (routes de l'API)

Ces tests appellent l'API avec `TestClient`. Ils n'ont jamais besoin d'une vraie base de données.

| Test | Ce qu'il fait | But | Résultat attendu |
| --- | --- | --- | --- |
| `test_hello` | Appelle `GET /hello`. | Vérifier la route affichée par le frontend. | `200` et `{"message": "Hello World"}`. |
| `test_health_db_ok` | Remplace la session de base par une session sur une base **SQLite en mémoire**, puis appelle `GET /health/db`. | Vérifier le cas nominal du contrôle de la base, sans PostgreSQL. | `200` et `{"status": "ok"}`. |
| `test_health_db_unavailable` | Remplace la session par un faux objet dont `execute` lève une `OperationalError`, l'erreur que SQLAlchemy lève quand la base est injoignable. | Vérifier qu'une panne de base devient une erreur d'API propre, sans détail interne. | `503` et `{"detail": "Base de données indisponible"}`. |

La fixture `clear_dependency_overrides` s'exécute automatiquement après chaque test (`autouse=True`) et retire les remplacements : les tests ne s'influencent jamais entre eux.

### 1.4 Tests unitaires : `tests/test_logging.py` (logs)

| Test | Ce qu'il fait | But | Résultat attendu |
| --- | --- | --- | --- |
| `test_log_level_defaults_to_info` | Supprime `LOG_LEVEL`, puis lit la configuration des logs. | Vérifier le niveau par défaut. | `log_level == "INFO"`. |
| `test_log_level_is_case_insensitive` | Définit `LOG_LEVEL=debug`. | On doit pouvoir écrire le niveau en minuscules. | `log_level == "DEBUG"`. |
| `test_invalid_log_level_is_rejected` | Définit `LOG_LEVEL=LOUD`. | Une faute de frappe doit être détectée au lieu d'être ignorée silencieusement. | Une `ValidationError` est levée. |
| `test_app_logs_use_uvicorn_format_and_respect_level` | Règle le niveau sur `WARNING`, écrit un log `info` et un log `warning`, et capture stderr avec `capsys`. | Vérifier le filtrage par niveau et le format de sortie. | Le message `info` est absent ; la sortie contient `WARNING:` et `app.example - visible message`. |
| `test_database_failure_is_logged_with_traceback` | Simule une base injoignable, appelle `GET /health/db` et capture stderr. | Une panne de base doit être visible dans les logs du serveur, avec le détail de l'erreur, pour le diagnostic. | `503` ; stderr contient `ERROR:`, `app.main - Échec de la connexion à la base de données` et `OperationalError`. |

Deux fixtures rendent ces tests indépendants :
- `no_env_file` place le test dans un dossier temporaire vide (`tmp_path`). Votre `.env` local n'est donc jamais lu, et seules les variables définies par le test comptent.
- `restore_default_logging` s'exécute après chaque test : elle remet la configuration des logs sur `INFO` et retire les remplacements de dépendances.

### 1.5 Tests d'intégration : `tests/integration/` (vrai PostgreSQL)

Ces tests vérifient ce que les faux objets ne peuvent pas vérifier : la vraie connexion, le vrai SQL et les migrations Alembic. Ils portent le marqueur `integration`.

Les fixtures de `tests/integration/conftest.py` préparent la base par étapes. Chaque étape s'appuie sur la précédente :

| Fixture | Portée | Ce qu'elle fait |
| --- | --- | --- |
| `test_database_url` | une fois par exécution | Lit la configuration PostgreSQL, se connecte au serveur et crée la base **`<POSTGRES_DB>_test`** (ex. `tierlist_test`) si elle n'existe pas. Les données de développement ne sont **jamais touchées**. |
| `migrated_engine` | une fois par exécution | Applique les migrations Alembic (`upgrade head`) sur la base de test, puis fournit un moteur de connexion. |
| `db_session` | à chaque test | Ouvre une transaction et donne au test une session à l'intérieur. À la fin du test, la transaction est **annulée** (*rollback*) : rien de ce que le test a écrit ne subsiste, et chaque test part d'une base propre. |
| `client` | à chaque test | Un `TestClient` dont la dépendance de base de données utilise `db_session`. |

| Test | Ce qu'il fait | But | Résultat attendu |
| --- | --- | --- | --- |
| `test_health_db_against_real_postgres` | Appelle `GET /health/db` avec la vraie session de base. | Vérifier toute la chaîne : configuration, SQLAlchemy, driver psycopg, PostgreSQL. | `200` et `{"status": "ok"}`. |

**Quand PostgreSQL n'est pas disponible :**
- **En local**, les tests d'intégration sont **ignorés** (*skipped*), avec le message `PostgreSQL is not reachable: start it with docker compose up -d --wait`. Les autres tests tournent quand même.
- **En CI** (`CI=true`), ils **échouent** : une base absente y est un vrai problème, qui ne doit pas être masqué.

---

## 2. Frontend (Vitest)

### 2.1 Fonctionnement de Vitest

- **Découverte** : Vitest exécute chaque fichier `*.test.ts` / `*.test.tsx`. Il est configuré dans le bloc `test` de `vite.config.ts`.
- **Structure** :
  - `describe('App', …)` regroupe des tests liés ;
  - `it('…', …)` est un test ;
  - `expect(valeur).toBe…()` est une assertion, et le test échoue si elle n'est pas vérifiée.
- **jsdom** : un navigateur simulé dans Node.js. On peut afficher et inspecter des composants sans ouvrir de vrai navigateur.
- **Testing Library** :
  - `render(<App />)` affiche le composant ;
  - `screen` cherche dans la page **comme un utilisateur la voit** : par texte visible (`getByText`) ou par rôle d'accessibilité (`getByRole('heading')`, `findByRole('alert')`) ;
  - `getBy…` cherche immédiatement, tandis que `findBy…` **attend** que l'élément apparaisse, ce qui est utile après un appel asynchrone.
- **jest-dom** : ajoute des assertions lisibles comme `toBeInTheDocument()` et `toHaveTextContent()`. Il est chargé par `src/test/setup.ts`, qui démonte aussi les composants après chaque test.
- **Simulations** (`vi.mock`, `vi.mocked`, `vi.spyOn`) : remplacent un module ou une fonction par une version factice dont le test décide le comportement. Ici, le module d'API (`src/api/hello.ts`) est simulé : les tests **n'appellent jamais le vrai backend**. Ils sont donc rapides et ne dépendent d'aucun serveur lancé.

### 2.2 Lancer les tests

| Commande (dans `frontend/`) | Effet |
| --- | --- |
| `pnpm test` | Lance tous les tests une fois |
| `pnpm test:watch` | Relance les tests concernés à chaque modification de fichier |
| `pnpm test:coverage` | Tous les tests, plus un tableau de couverture de `src/` |

### 2.3 Tests : `src/App.test.tsx`

`getHello` (l'appel `GET /api/hello`) est simulé. Avant chaque test, `mockReset()` efface le comportement précédent.

| Test | Ce qu'il fait | But | Résultat attendu |
| --- | --- | --- | --- |
| `shows a loading message while the backend answers` | `getHello` renvoie une promesse qui ne se termine jamais, ce qui simule un backend lent. | Vérifier l'état de chargement. | Le texte `Chargement…` est affiché. |
| `shows the message returned by the backend` | `getHello` renvoie `{ message: 'Hello World' }`. | Vérifier l'état de succès : le message du backend est affiché. | Un titre (`<h1>`) avec le texte `Hello World` apparaît. |
| `shows an alert when the backend cannot be reached` | `getHello` échoue avec une erreur. `console.error` est rendu silencieux avec `vi.spyOn` et vérifié. | Vérifier l'état d'erreur : l'utilisateur est prévenu, et l'erreur est journalisée pour les développeurs. | Un élément de rôle `alert` contient `Impossible de joindre le backend`, et `console.error` a été appelé. |

---

## 3. Lire les résultats

| Résultat | Signification |
| --- | --- |
| `passed` / ✓ | Le test s'est exécuté et toutes ses assertions sont vérifiées. |
| `failed` / ✗ | Une assertion n'est pas vérifiée, ou une erreur inattendue a été levée. La sortie montre la valeur attendue et la valeur obtenue. |
| `skipped` (backend) | Le test n'a pas été exécuté, avec la raison dans la sortie (`uv run pytest -rs` liste les raisons). Aujourd'hui, cela n'arrive que pour les tests d'intégration quand PostgreSQL ne tourne pas en local. |
| `error` (backend) | Une fixture a échoué avant que le test puisse s'exécuter, par exemple pas de base en CI. |

**La couverture** indique, pour chaque fichier, la part du code exécutée par les tests :
- backend (pytest-cov) : `Stmts` (instructions), `Miss` (instructions qu'aucun test n'a exécutées) et `Cover` (pourcentage) ;
- frontend (Vitest) : `% Stmts` (instructions), `% Branch` (chemins `if`/`else`), `% Funcs` (fonctions), `% Lines` (lignes) et `Uncovered Line #s` (lignes qu'aucun test n'a exécutées).

Il n'y a pas de seuil minimal pour l'instant. La couverture aide à repérer le code non testé, mais elle ne prouve pas que les tests sont bons.

---

## 4. Écrire un nouveau test

1. **Tester le comportement, pas l'implémentation** :
   - backend : vérifier le statut HTTP et le JSON renvoyé ;
   - frontend : vérifier ce que voit l'utilisateur, avec les textes et les rôles.
2. **Un test, un comportement**, avec un nom qui dit ce qui est attendu, par exemple `test_invalid_log_level_is_rejected`.
3. **Couvrir les cas d'erreur et les cas limites**, pas seulement le cas nominal.
4. **Garder les tests indépendants** : utiliser des fixtures et `dependency_overrides`, et nettoyer après le test (fixtures `autouse`, `mockReset`).
5. **Choisir le bon niveau** :
   - un test unitaire avec de faux objets pour la logique et le contrat d'API ;
   - un test d'intégration (`tests/integration/`, marqueur `integration`) dès que du vrai SQL ou des migrations entrent en jeu.
6. Placer les nouveaux tests frontend à côté du composant (`Composant.test.tsx`), et les nouveaux tests backend dans `backend/tests/`.
7. Lancer les tests en local avant de pousser ; la CI les relance sur la PR.
