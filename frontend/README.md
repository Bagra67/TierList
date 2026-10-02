# TierList — Frontend

Frontend **React 19 + TypeScript**, construit avec **Vite**, qui affiche le message renvoyé par `GET /hello` du backend. Outillage :

- **ESLint + Prettier** pour le lint et le formatage automatiques ;
- **pnpm** comme gestionnaire de paquets.

> Ce dossier fait partie du dépôt [TierList](../README.md). **Toutes les commandes ci-dessous se lancent depuis le dossier `frontend/`** (`cd frontend`).

---

## 1. Prérequis

- **Node.js 20.19+** (LTS recommandée) : `node --version`
- **pnpm** : `npm install -g pnpm`, puis `pnpm --version`

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

Pour que le message s'affiche, lancez aussi le backend dans un autre terminal (`cd backend` puis `uv run fastapi dev app/main.py`).
Les appels vers `/api/...` sont redirigés vers `http://127.0.0.1:8000/...` par le proxy configuré dans `vite.config.ts`.

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
│   │   └── hello.ts        # Appel GET /api/hello vers le backend FastAPI
│   ├── App.tsx             # Affiche le message du backend
│   └── main.tsx            # Point d'entrée React
├── eslint.config.js
├── vite.config.ts          # Config Vite + proxy /api vers le backend
└── package.json
```
