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

Les tests utilisent **Vitest** (jsdom) et **Testing Library**, configurés dans le bloc `test` de `vite.config.ts`. Les fichiers de test sont à côté du code (`*.test.tsx`), et `fetch` est simulé (`vi.stubGlobal`) : les tests n'appellent jamais le backend. La CI lance `pnpm test:coverage`. Détail de chaque test : [guide des tests](../docs/testing.fr.md).

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

`pnpm format` et `pnpm format:check` couvrent aussi le dossier `docs/` du dépôt, avec le même `.prettierrc` (la CI le vérifie aussi). Le hook pre-commit ne formate pas `docs/` : lancez `pnpm format` avant de commiter une modification de doc.

---

## 6. Structure du projet

```
frontend/
├── public/                 # Fichiers statiques servis tels quels (favicon…)
├── src/
│   ├── api/
│   │   ├── client.ts       # Client HTTP commun (openapi-fetch), ApiError, access token + middleware de rafraîchissement
│   │   ├── queryClient.ts  # Configuration TanStack Query (nouvel essai, log des erreurs)
│   │   ├── auth.ts         # Appels /auth + hooks useCurrentUser, useLogin, useRegister, useLogout
│   │   ├── hello.ts        # GET /hello : getHello() + hook useHello()
│   │   ├── *.test.ts       # Tests de la couche API
│   │   └── schema.d.ts     # Types d'API générés depuis backend/openapi.json (ne pas modifier)
│   ├── auth/RequireAuth.tsx # Garde des routes privées (redirige vers /login)
│   ├── components/         # Composants réutilisables (TextField)
│   ├── pages/              # Un composant par route (HomePage, LoginPage, RegisterPage) + tests
│   ├── test/
│   │   ├── setup.ts        # Préparation des tests (matchers jest-dom, nettoyage)
│   │   ├── renderWithQueryClient.tsx # render() dans un QueryClient neuf
│   │   └── stubBackend.ts  # Faux backend qui remplace fetch, route par route
│   ├── App.tsx             # Routes (react-router)
│   ├── App.test.tsx        # Tests du routage : redirection, restauration de session, déconnexion
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

---

## 8. Récupération des données

Les données du serveur passent par **TanStack Query**, au-dessus d'un client **openapi-fetch** commun. Les composants n'appellent jamais `fetch` ni `useEffect` pour charger des données :

```
Composant → hook useX() (TanStack Query) → getX() → apiClient (openapi-fetch) → /api → FastAPI
```

- `src/api/client.ts` : `apiClient`, le seul client HTTP. Ses chemins, paramètres et réponses sont typés par `schema.d.ts` : un chemin ou un champ erroné est une erreur de `pnpm typecheck`. `ApiError` (`status`, `body`, et le `detail` du backend comme `message`) est levée pour toute réponse hors 2xx.
- `src/api/queryClient.ts` : `createQueryClient()`, utilisé par `main.tsx`. Il refait une fois une requête en échec et journalise chaque échec dans la console, à un seul endroit.
- TanStack Query gère les états de chargement et d'erreur, l'annulation au démontage, le cache (une même `queryKey` n'est récupérée qu'une fois) et le rafraîchissement.

Pour ajouter un endpoint, créez `src/api/<ressource>.ts` sur le modèle de `hello.ts` :

```ts
export async function getHello(signal?: AbortSignal): Promise<HelloResponse> {
  const { data, error, response } = await apiClient.GET('/hello', { signal });
  if (data === undefined) {
    throw new ApiError(response.status, error);
  }
  return data;
}

export function useHello() {
  return useQuery({ queryKey: ['hello'], queryFn: ({ signal }) => getHello(signal) });
}
```

Le composant ne fait alors que lire l'état : `const { data, isPending, isError } = useHello();`.

Dans les tests, affichez les composants avec `renderWithQueryClient` (`src/test/`) et simulez `fetch` avec `stubBackend`, comme dans `App.test.tsx`.

### Requêtes authentifiées

`apiClient` ajoute l'access token (gardé en mémoire) à chaque requête. Quand une requête reçoit une `401`, il rafraîchit le token une fois via `POST /auth/refresh` (cookie de refresh) et renvoie la requête ; les requêtes simultanées partagent le même rafraîchissement. Rien à faire dans un nouveau `api/<ressource>.ts`. L'utilisateur courant se lit avec `useCurrentUser()`, et les pages privées se placent sous la route `RequireAuth` de `App.tsx`. Détails : [guide de l'authentification](../docs/authentication.fr.md).
