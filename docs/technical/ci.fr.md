# Intégration continue

[English](ci.md) | Français

Comment les workflows GitHub Actions s'enchaînent, pourquoi la CI est construite ainsi, et comment la garder rapide. Les jobs et leurs étapes sont listés dans le [README](../../README.fr.md#intégration-continue-github-actions) ; chaque test est décrit dans le [guide des tests](testing.fr.md).

## 1. Les workflows et leur enchaînement

| Workflow      | Se lance                                                                       | Fait                                                                                                                |
| ------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------- |
| `ci.yml`      | sur chaque PR ; sur un push sur `develop` ou `main`                            | `Changed parts`, `Backend`, `Frontend`, `Secrets`                                                                   |
| `docs.yml`    | sur chaque PR (aussi quand un label change) ; sur un push sur `develop`/`main` | `Docs` : docs bilingues et guide des tests synchronisés                                                             |
| `deploy.yml`  | après un run `CI` ou `Release` terminé de `develop` ou `main` ; à la main      | le staging après un push CI sur `develop`, la production après `Release` ([guide du déploiement](deployment.fr.md)) |
| `release.yml` | après un push CI terminé sur `main`                                            | crée le tag `vX.Y.Z` et publie la GitHub Release ([guide des versions](releasing.fr.md))                            |
| `bundle.yml`  | appelé par `deploy.yml`                                                        | construit l'archive déployée sur les pods                                                                           |
| `backup.yml`  | chaque nuit ; à la main                                                        | sauvegarde de la base                                                                                               |

```text
PR ──> CI + Docs (contrôles requis) ──squash──> push develop ──> CI ──> Deploy (staging)
PR de release develop ──> main ──merge commit──> push main ──> CI ──> Release ──> Deploy (production)
```

`Deploy` et `Release` partent de `workflow_run`, que GitHub lit depuis la branche par défaut (`develop`) : une modification de ces fichiers ne s'applique qu'une fois fusionnée dans `develop`. `Deploy` filtre les runs terminés sur `develop` et `main` ; un run `Release` compte comme un run de `develop`, puisqu'un `workflow_run` tourne sur la branche par défaut.

## 2. Seulement ce qu'une PR touche

Le job `Changed parts` (quelques secondes) liste les fichiers de la PR par l'API GitHub, puis `Backend` et `Frontend` ne tournent que pour leur partie :

| Fichiers de la PR                                          | Backend | Frontend |
| ---------------------------------------------------------- | :-----: | :------: |
| `backend/…`                                                |    ✓    |          |
| `backend/openapi.json` (les types du frontend en viennent) |    ✓    |    ✓     |
| `frontend/…`, `docs/…` (Prettier vérifie `docs/`)          |         |    ✓     |
| autres fichiers Markdown (README, `AGENTS.md`…)            |         |          |
| tout autre fichier (`.github/`, `compose.yaml`…)           |    ✓    |    ✓     |

- Un **job sauté compte comme réussi** pour les contrôles requis : les rulesets ne changent pas.
- Un **push sur `develop` ou `main` lance toujours tout** : il déploie le staging ou crée la release.
- **Dans le doute, tout tourne** : un fichier inconnu, une erreur de l'API ou un job `Changed parts` en échec.
- Un nouveau type de fichier qu'un seul côté vérifie demande une ligne dans le `case` de `ci.yml` ; sinon les deux jobs tournent pour lui (sans risque, juste plus lent).

## 3. Choix pour la vitesse

Mesurés pendant le spike #246 sur `ubuntu-latest` (4 vCPU), médiane de plusieurs runs :

| Changement                                               | Effet                                                                                                          |
| -------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Développement en Python 3.13, la version des pods        | la suite tourne une fois au lieu de deux (3.11, puis 3.13) ; `Backend` ≈ 241 s → ≈ 112 s                       |
| Couverture par `sys.monitoring` (`COVERAGE_CORE=sysmon`) | la couverture ne coûte presque plus rien ; couverture des lignes seulement (les branches ne sont pas mesurées) |
| SeaweedFS démarré en arrière-plan                        | ses 14 s de démarrage se superposent à l'installation et aux vérifications ; `Backend` ≈ 100 s                 |
| `pytest -n auto` (pytest-xdist)                          | tests ≈ 64 s → ≈ 57 s ; `Backend` ≈ 90 s                                                                       |
| Fichiers Vitest non isolés (`isolate: false`)            | Vitest 25–40 s → ≈ 10 s ; `Frontend` ≈ 55 s                                                                    |

Gardés tels quels, volontairement :

- **Docs sur les événements de label** : créer une PR avec des labels lance `Docs` plusieurs fois (≈ 10 s chacun). Sauter ces runs afficherait un contrôle `Docs` _sauté_, donc réussi, sur un commit dont un run précédent a échoué.
- **CI sur le push après un merge** : il refait tourner l'arbre déjà testé par la PR, mais sa réussite autorise le déploiement staging et la release.
- **Jobs frontend en parallèle** (lint, `tsc`, knip, build) : chaque nouveau job paie sa propre installation (≈ 20 s) pour gagner environ 5 s.
- **Python 3.14** : la suite passe, mais il n'est pas plus rapide que la 3.13 avec `sysmon`, et il dépend du Python des pods.

## 4. La garder rapide et fiable

- Les tests backend doivent fonctionner en parallèle : aucun nom fixe partagé entre tests dans la base ou le bucket S3, et aucune valeur aléatoire dans une liste de `parametrize` (chaque worker doit collecter les mêmes noms de tests). Voir le [guide des tests](testing.fr.md#15-tests-dintégration--testsintegration-vrais-postgresql-et-s3).
- Les fichiers de test frontend partagent leurs modules et jsdom : un fichier remet en place ce qu'il change, et le setup commun remet le reste à zéro. Les attentes utilisent la limite commune de 3 s. Voir le [guide des tests](testing.fr.md).
- Le résumé de chaque run liste les tests les plus lents de chaque job : un test qui y grimpe mérite un coup d'œil.
