# TierList — Frontend

Frontend **React 19 + TypeScript**, construit avec **Vite**, avec :

- **Redux Toolkit** pour le store (slices + **RTK Query** pour les appels à l'API) ;
- **Material UI** (version gratuite, `@mui/material`) pour les composants ;
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

Pour que les données s'affichent, lancez aussi le backend dans un autre terminal (`cd backend` puis `uv run fastapi dev app/main.py`).
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
│   ├── app/
│   │   ├── store.ts        # configureStore + types RootState / AppDispatch
│   │   └── hooks.ts        # useAppDispatch / useAppSelector typés
│   ├── features/
│   │   ├── api/
│   │   │   └── apiSlice.ts # RTK Query : appels au backend FastAPI
│   │   └── counter/
│   │       └── counterSlice.ts # Exemple de slice Redux classique
│   ├── App.tsx             # Page d'exemple (composants MUI)
│   ├── main.tsx            # Point d'entrée : Provider Redux + ThemeProvider MUI
│   └── theme.ts            # Thème Material UI
├── eslint.config.js
├── vite.config.ts          # Config Vite + proxy /api vers le backend
└── package.json
```

---

## 7. Recettes

### Ajouter un slice Redux

1. Créez `src/features/<nom>/<nom>Slice.ts` avec `createSlice` (voir `counterSlice.ts`).
2. Ajoutez son reducer dans `src/app/store.ts` :
   ```ts
   reducer: {
     counter: counterReducer,
     monSlice: monSliceReducer,
     [apiSlice.reducerPath]: apiSlice.reducer,
   },
   ```
3. Dans un composant : `useAppSelector((state) => state.monSlice...)` et `useAppDispatch()`.

### Ajouter un appel à l'API (RTK Query)

Dans `src/features/api/apiSlice.ts`, ajoutez un endpoint puis exportez son hook :

```ts
getItem: builder.query<Item, number>({
  query: (id) => `/items/${id}`,
}),
```

```ts
export const { useGetItemQuery } = apiSlice;
// Dans un composant :
const { data, isLoading, isError } = useGetItemQuery(1);
```

Utilisez `builder.mutation` pour les POST/PUT/DELETE, et `providesTags` / `invalidatesTags` pour rafraîchir automatiquement les données (voir `getItems` / `addItem`).

### Utiliser un composant Material UI

```tsx
import { Button } from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';

<Button variant="contained" startIcon={<SaveIcon />}>
  Enregistrer
</Button>;
```

Catalogue des composants : https://mui.com/material-ui/all-components/ — icônes : https://mui.com/material-ui/material-icons/
Le style se fait avec la prop `sx` ou via le thème dans `src/theme.ts`.
