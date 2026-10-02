# Publier une release

[English](releasing.md) | Français

Chaque fusion de `develop` dans `main` est une **release** avec un numéro de version `X.Y.Z` ([Semantic Versioning](https://semver.org/lang/fr/)), un tag `vX.Y.Z` et une GitHub Release. La version est **calculée à partir des messages de commit** de `develop` (Conventional Commits, vérifiés par commitlint), et non choisie à la main.

## Règles de version

| Commit squashé sur `develop`                                | Effet sur la version           | Exemple                                  |
| ----------------------------------------------------------- | ------------------------------ | ---------------------------------------- |
| `!` après le type, ou pied `BREAKING CHANGE:`               | **X** + 1 (en 0.x : **Y** + 1) | `feat(api)!: rename /hello to /greeting` |
| `feat`                                                      | **Y** + 1                      | `feat(backend): add tier lists`          |
| `fix`, `perf`                                               | **Z** + 1                      | `fix(frontend): keep the items order`    |
| `docs`, `chore`, `ci`, `build`, `test`, `refactor`, `style` | aucun                          | figurent quand même dans le CHANGELOG    |

Le changement le plus fort depuis la dernière release l'emporte : un `feat` et trois `fix` donnent une release **Y**.

- **Une seule version pour tout le dépôt**, inscrite dans `backend/pyproject.toml`, `frontend/package.json` et `app.version` (`backend/app/main.py`, reprise dans `openapi.json`). Le test `test_versions_are_in_sync` vérifie qu'elles sont égales.
- **Phase 0.x** : tant que la version est en 0.x, l'API n'est pas stable et un breaking change n'incrémente que **Y**. Le passage en **1.0.0** est une décision volontaire (première version pour de vrais utilisateurs) : `./scripts/prepare-release.sh --version 1.0.0`.
- **Les breaking changes doivent se voir** : le titre squash de la PR porte `!` (`feat(api)!: …`) et son corps explique la migration dans un pied `BREAKING CHANGE: …`. Les relecteurs le vérifient avant la fusion.
- **Les tags `vX.Y.Z` n'existent que sur `main`**, créés par le workflow `Release`, jamais à la main et jamais sur `develop`.
- **Le CHANGELOG est généré** (`CHANGELOG.md`, par [git-cliff](https://git-cliff.org) avec `cliff.toml`) et relu dans la PR de préparation. Une ligne peut être corrigée à la main ; les sections publiées ne sont jamais régénérées.
- **Aucun commit direct ni hotfix sur `main`** : un correctif passe par `develop`, puis une release **Z**.

## Faire une release

1. **Préparer** sur une nouvelle branche partie de `develop` à jour :

   ```bash
   git switch develop && git pull
   ./scripts/prepare-release.sh --dry-run          # affiche la version calculée
   git switch -c chore/release-vX.Y.Z
   ./scripts/prepare-release.sh                    # ou --version X.Y.Z pour l'imposer
   ```

   Le script met à jour les trois champs de version, régénère `openapi.json` et `schema.d.ts`, et ajoute la nouvelle section en tête de `CHANGELOG.md`. Il refuse de tourner s'il n'y a rien à publier (aucun `feat`, `fix`, `perf` ni breaking change depuis le dernier tag) ou si la branche ne part pas d'`origin/develop`.

   Relisez `CHANGELOG.md`, puis commitez `chore(release): prepare vX.Y.Z`, ouvrez une PR vers `develop` et fusionnez-la en squash.

2. **Publier** : ouvrez une PR de `develop` vers `main` intitulée `chore(release): vX.Y.Z` et fusionnez-la avec un **merge commit** (AGENTS.md §40).

3. **Automatique** : quand la CI passe sur `main`, le workflow `Release` (`.github/workflows/release.yml`) vérifie que les versions sont égales, que le tag n'existe pas encore et que `CHANGELOG.md` contient la section, puis crée le tag `vX.Y.Z` sur le merge commit et la GitHub Release avec cette section comme notes. Si une vérification échoue, le workflow échoue avec la raison et rien n'est publié.

## Calcul de la version

Les tags sont sur les merge commits de `main`, que `develop` ne contient pas. Le script prend donc le plus grand tag `vX.Y.Z` du dépôt et analyse les commits de `vX.Y.Z..HEAD` : cette plage exclut tout ce qui a déjà été publié.
