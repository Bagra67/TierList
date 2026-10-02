# TierList — Frontend

[English](README.md) | Français

Frontend **React 19 + TypeScript**, construit avec **Vite**, qui affiche le message renvoyé par `GET /hello` du backend. Outillage :

- **ESLint + Prettier** pour le lint et le formatage automatiques ;
- **pnpm** comme gestionnaire de paquets.

> Ce dossier fait partie du dépôt [TierList](../README.fr.md). **Toutes les commandes ci-dessous se lancent depuis le dossier `frontend/`** (`cd frontend`).

---

## 1. Prérequis

- **Node.js 24 LTS** (version épinglée dans `.nvmrc` à la racine du dépôt) : `node --version`
- **pnpm** : `npm install -g pnpm`, puis `pnpm --version`. La version exacte est épinglée dans le champ `packageManager` de `package.json` et verrouillée dans `pnpm-lock.yaml`.

---

## 2. Installer le projet

```bash
pnpm install
```

Installe les dépendances aux versions exactes de `pnpm-lock.yaml` et active le hook git (husky) via le script `prepare`.

---

## 3. Lancer le projet

| Action                                | Commande                           |
| ------------------------------------- | ---------------------------------- |
| Serveur de dev (rechargement à chaud) | `pnpm dev` → http://localhost:5173 |
| Build de production (dans `dist/`)    | `pnpm build`                       |
| Prévisualiser le build                | `pnpm preview`                     |
| Vérifier les types TypeScript         | `pnpm typecheck`                   |
| Lancer les tests (Vitest)             | `pnpm test`                        |
| Tests en mode surveillance            | `pnpm test:watch`                  |
| Tests avec couverture                 | `pnpm test:coverage`               |

Pour que le message s'affiche, lancez aussi le backend dans un autre terminal (`cd backend` puis `uv run fastapi dev app/main.py`).
Les appels vers `/api/...` sont redirigés vers `http://127.0.0.1:8000/...` par le proxy configuré dans `vite.config.ts`.

Les tests utilisent **Vitest** (jsdom) et **Testing Library**, configurés dans le bloc `test` de `vite.config.ts`. Les fichiers de test sont à côté du code (`*.test.tsx`), et le module d'API est simulé : les tests n'appellent jamais le backend. La CI lance `pnpm test:coverage`. Détail de chaque test : [guide des tests](../docs/testing.fr.md).

---

## 4. Gérer les packages

> ⚠️ Utilisez toujours `pnpm` (pas `npm install` ni `yarn`) pour garder `pnpm-lock.yaml` cohérent.

| Action                                         | Commande                                                    |
| ---------------------------------------------- | ----------------------------------------------------------- |
| Ajouter un package                             | `pnpm add <package>` (ex : `pnpm add react-router`)         |
| Ajouter une version précise                    | `pnpm add <package>@<version>` (ex : `pnpm add dayjs@1.11`) |
| Ajouter un package de dev                      | `pnpm add -D <package>` (ex : `pnpm add -D vitest`)         |
| Supprimer un package                           | `pnpm remove <package>`                                     |
| Mettre à jour un package                       | `pnpm update <package>`                                     |
| Mettre à jour vers la dernière version majeure | `pnpm update <package> --latest`                            |
| Voir les packages obsolètes                    | `pnpm outdated`                                             |
| Lister les packages installés                  | `pnpm list`                                                 |
| Lancer un binaire installé                     | `pnpm exec <commande>`                                      |

---

## 5. Lint et formatage

| Action                              | Commande            |
| ----------------------------------- | ------------------- |
| Analyser le code (ESLint)           | `pnpm lint`         |
| Corriger automatiquement            | `pnpm lint:fix`     |
| Formater tout le code (Prettier)    | `pnpm format`       |
| Vérifier le formatage sans modifier | `pnpm format:check` |

C'est automatique à deux endroits :

- **À l'enregistrement dans VS Code** : formatage Prettier + corrections ESLint. Installez les extensions recommandées (VS Code les propose à l'ouverture du dossier `TierList`) : ESLint et Prettier.
- **Avant chaque commit** : le hook husky lance `lint-staged`, qui corrige et formate les fichiers modifiés. Si une erreur ESLint ne peut pas être corrigée automatiquement, le commit est bloqué.

Configuration : `eslint.config.js`, `.prettierrc`, `.prettierignore`, section `lint-staged` de `package.json`.

---

## 6. Structure du projet

```
frontend/
├── public/                 # Fichiers statiques servis tels quels (favicon…)
├── src/
│   ├── api/
│   │   ├── hello.ts        # Appel GET /api/hello vers le backend FastAPI
│   │   └── schema.d.ts     # Types d'API générés depuis backend/openapi.json (ne pas modifier)
│   ├── test/
│   │   └── setup.ts        # Préparation des tests (matchers jest-dom, nettoyage)
│   ├── App.tsx             # Affiche le message du backend
│   ├── App.test.tsx        # Tests d'App : chargement, message, erreur
│   └── main.tsx            # Point d'entrée React
├── eslint.config.js
├── vite.config.ts          # Config Vite + proxy /api + config Vitest
└── package.json
```

---

## 7. Types d'API (générés)

Les types d'API ne sont **jamais écrits à la main** : `src/api/schema.d.ts` est généré par `pnpm gen:api` à partir de `backend/openapi.json`, le contrat exporté par le backend. Utilisez-les via `components['schemas'][...]`, comme dans `src/api/hello.ts` :

```ts
import type { components } from './schema';

export type HelloResponse = components['schemas']['HelloResponse'];
```

Un changement du backend qui casse le frontend devient alors une erreur de `pnpm typecheck`.

Quand vous ajoutez ou modifiez une route ou un schéma Pydantic :

1. `uv run python scripts/export_openapi.py` (dans `backend/`) met à jour `openapi.json` ;
2. `pnpm gen:api` (dans `frontend/`) régénère les types TypeScript ;
3. corrigez les éventuelles erreurs de `pnpm typecheck` : elles montrent le code frontend touché par le changement ;
4. commitez ensemble `backend/openapi.json` et `frontend/src/api/schema.d.ts`.

Si vous oubliez l'étape 1, le test backend `test_openapi_schema_is_up_to_date` échoue ; si vous oubliez l'étape 2, l'étape CI « Check API types are up to date » échoue.
