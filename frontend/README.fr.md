# TierList — Frontend

[English](README.md) | Français

Frontend **React 19 + TypeScript**, construit avec **Vite**, l'interface web de TierList (comptes, connexion, confirmation de l'email, mot de passe oublié). Outillage :

- **ESLint + Prettier** pour le lint et le formatage automatiques ;
- **pnpm** comme gestionnaire de paquets.

> Ce dossier fait partie du dépôt [TierList](../README.fr.md). **Toutes les commandes ci-dessous se lancent depuis le dossier `frontend/`** (`cd frontend`).

---

## 1. Prérequis

- **Node.js 26** (version épinglée dans `.nvmrc` à la racine du dépôt) : `node --version`
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

Les tests utilisent **Vitest** (jsdom) et **Testing Library**, configurés dans le bloc `test` de `vite.config.ts`. Les fichiers de test sont à côté du code (`*.test.tsx`), et `fetch` est simulé (`vi.stubGlobal`) : les tests n'appellent jamais le backend. La CI lance `pnpm test:coverage`. Détail de chaque test : [guide des tests](../docs/technical/testing.fr.md).

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

| Action                                              | Commande            |
| --------------------------------------------------- | ------------------- |
| Analyser le code (ESLint)                           | `pnpm lint`         |
| Corriger automatiquement                            | `pnpm lint:fix`     |
| Formater tout le code (Prettier)                    | `pnpm format`       |
| Vérifier le formatage sans modifier                 | `pnpm format:check` |
| Trouver exports, fichiers et dépendances inutilisés | `pnpm knip`         |

C'est automatique à deux endroits :

- **À l'enregistrement dans VS Code** : formatage Prettier + corrections ESLint. Installez les extensions recommandées (VS Code les propose à l'ouverture du dossier `TierList`) : ESLint et Prettier.
- **Avant chaque commit** : le hook husky lance `lint-staged`, qui corrige et formate les fichiers modifiés. Si une erreur ESLint ne peut pas être corrigée automatiquement, le commit est bloqué.

ESLint vérifie aussi l'**accessibilité** avec `eslint-plugin-jsx-a11y-x` (règles `recommended`) : textes alternatifs (`alt`), labels, rôles et attributs ARIA valides, utilisation au clavier des éléments cliquables. C'est le fork maintenu d'`eslint-plugin-jsx-a11y`, avec les mêmes règles, choisi car l'original ne prend pas en charge ESLint 10. Il repère ce qui se voit dans le code ; le focus, le contraste et le comportement avec un lecteur d'écran restent à vérifier dans le navigateur.

**knip** liste ce que rien n'utilise : exports, fichiers et dépendances (`knip.jsonc` : `schema.d.ts` et les exports shadcn de `src/components/ui/` sont ignorés, `git-cliff` est lancé par `scripts/prepare-release.sh`). Il tourne en CI : supprimez ce qu'il signale, ou expliquez l'exception dans `knip.jsonc`.

**Où ranger un type ou une interface** :

- utilisé par **un seul fichier** (props d'un composant, types internes) : il reste dans ce fichier, **sans `export`**. TypeScript interdit alors à tout autre fichier de s'en servir.
- nécessaire à **un deuxième fichier** : on l'exporte depuis le module auquel il appartient (ex. `src/api/<ressource>.ts` pour les types d'API, issus de `schema.d.ts`) et on l'importe de là.
- `pnpm typecheck` bloque l'usage d'un type non exporté, et `pnpm knip` signale un export que personne n'importe. Seul un type recopié au lieu d'être importé reste à vérifier en review.

Configuration : `eslint.config.js`, `.prettierrc`, `.prettierignore`, section `lint-staged` de `package.json`.

`pnpm format` et `pnpm format:check` couvrent aussi le dossier `docs/` du dépôt, avec le même `.prettierrc` (la CI le vérifie aussi). Le hook pre-commit ne formate pas `docs/` : lancez `pnpm format` avant de commiter une modification de doc.

---

## 6. Structure du projet

```
frontend/
├── public/                 # Fichiers statiques servis tels quels (favicon…)
├── src/
│   ├── api/
│   │   ├── client.ts       # Client HTTP commun (openapi-fetch), access token + middleware de rafraîchissement
│   │   ├── queryClient.ts  # Configuration TanStack Query (nouvel essai, log des erreurs)
│   │   ├── auth.ts         # Appels /auth + hooks useCurrentUser, useLogin, useRegister, useLogout
│   │   ├── templates.ts    # Appels /templates + hooks useTemplates, useTemplate, useCreateTemplate, useDeleteTemplate
│   │   ├── *.test.ts       # Tests de la couche API
│   │   └── schema.d.ts     # Types d'API générés depuis backend/openapi.json (ne pas modifier)
│   ├── auth/               # Gardes de routes : RequireAuth (pages privées → /login), RedirectIfSignedIn (/login, /register → là où l'utilisateur allait)
│   ├── components/         # Composants réutilisables (Layout, AuthPageShell, ErrorMessage, ErrorBoundary, LanguageSwitcher, ThemeSwitcher, TextField, DeleteAccountDialog, GoogleSignInLink, EmailVerificationBanner, MainNav, CreateTemplateDialog, DeleteTemplateDialog)
│   │   └── ui/             # Composants shadcn/ui (button, input, label, card), modifiables
│   ├── constants/          # Valeurs fixes : auth.ts, routes.ts, http.ts, i18n.ts, templates.ts, theme.ts
│   ├── errors/             # ApiError, getFieldErrors, traduction des codes d'erreur (+ tests)
│   ├── i18n/               # Traductions : mise en place, locales/fr.ts et en.ts (+ tests)
│   ├── lib/utils.ts        # cn() : fusionne les classes Tailwind (utilisé par shadcn/ui)
│   ├── theme/              # Mode sombre : préférence de thème, classe dark sur <html> (+ tests)
│   ├── pages/              # Un composant par route (HomePage, LoginPage, RegisterPage, VerifyEmailPage, ForgotPasswordPage, ResetPasswordPage, TemplatesPage, TemplateEditorPage) + tests
│   ├── test/
│   │   ├── setup.ts        # Préparation des tests (matchers jest-dom, nettoyage, français par défaut)
│   │   ├── renderWithQueryClient.tsx # render() dans un QueryClient neuf
│   │   ├── matchMedia.ts   # Faux matchMedia : thème clair / sombre du système
│   │   └── stubBackend.ts  # Faux backend qui remplace fetch, route par route
│   ├── App.tsx             # Routes (react-router), dans le Layout commun
│   ├── App.test.tsx        # Tests du routage : redirection, restauration de session, déconnexion
│   ├── index.css           # Tailwind CSS + thème shadcn/ui (couleurs, arrondis, police)
│   └── main.tsx            # Point d'entrée React
├── components.json         # Config de la CLI shadcn/ui (style, alias)
├── index.html              # Page HTML + script qui applique le thème avant l'application
├── eslint.config.js
├── vite.config.ts          # Config Vite (React, Tailwind CSS, alias @/) + proxy /api + config Vitest
└── package.json
```

---

## 7. Types d'API (générés)

Les types d'API ne sont **jamais écrits à la main** : `src/api/schema.d.ts` est généré par `pnpm gen:api` à partir de `backend/openapi.json`, le contrat exporté par le backend. Utilisez-les via `components['schemas'][...]`, comme dans `src/api/auth.ts` :

```ts
import type { components } from './schema';

export type User = components['schemas']['UserResponse'];
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

- `src/api/client.ts` : `apiClient`, le seul client HTTP. Ses chemins, paramètres et réponses sont typés par `schema.d.ts` : un chemin ou un champ erroné est une erreur de `pnpm typecheck`. `ApiError` (`src/errors/apiError.ts` : `status`, `body`, le `code` et les `params` de l'API, et le `detail` du backend comme `message`) est levée pour toute réponse hors 2xx. Les composants affichent `translateError(t, error)`, jamais `error.message`. Les valeurs fixes (routes, statuts HTTP, limites) viennent de `src/constants/`.
- `src/api/queryClient.ts` : `createQueryClient()`, utilisé par `main.tsx`. Il refait une fois une requête en échec et journalise chaque échec dans la console, à un seul endroit.
- TanStack Query gère les états de chargement et d'erreur, l'annulation au démontage, le cache (une même `queryKey` n'est récupérée qu'une fois) et le rafraîchissement.

Pour ajouter un endpoint, créez `src/api/<ressource>.ts` sur le modèle de `auth.ts`, par exemple une lecture :

```ts
export async function getMe(signal?: AbortSignal): Promise<User> {
  return dataOrThrow(await apiClient.GET('/auth/me', { signal }));
}

export function useMe() {
  return useQuery({ queryKey: ['me'], queryFn: ({ signal }) => getMe(signal) });
}
```

`dataOrThrow` (`src/api/client.ts`) renvoie le corps d'une réponse réussie et lève `ApiError` sinon ; `throwIfError` fait de même pour les réponses sans corps (`204`). Le composant ne fait alors que lire l'état : `const { data, isPending, isError } = useMe();`.

Dans les tests, affichez les composants avec `renderWithQueryClient` (`src/test/`) et simulez `fetch` avec `stubBackend`, comme dans `App.test.tsx`.

### Requêtes authentifiées

`apiClient` ajoute l'access token (gardé en mémoire) à chaque requête. Quand une requête reçoit une `401`, il rafraîchit le token une fois via `POST /auth/refresh` (cookie de refresh) et renvoie la requête ; les requêtes simultanées partagent le même rafraîchissement. Rien à faire dans un nouveau `api/<ressource>.ts`. L'utilisateur courant se lit avec `useCurrentUser()`, et les pages privées se placent sous la route `RequireAuth` de `App.tsx`. Détails : [guide de l'authentification](../docs/technical/authentication.fr.md).

---

## 9. Traductions

Tout texte affiché passe par `t()` de `react-i18next`, et l'interface existe en français et en anglais (sélecteur de langue dans l'en-tête de chaque page) :

```tsx
const { t } = useTranslation();
return <h1>{t('auth.login.title')}</h1>;
```

- Les textes sont dans `src/i18n/locales/fr.ts` (référence) et `en.ts` ; une clé absente ou en trop dans `en.ts` est une erreur de `pnpm typecheck`, et les clés de `t('…')` sont vérifiées au typage elles aussi.
- Les erreurs de l'API sont traduites à partir de leur code : `translateError(t, error)` et `translateFieldError(t, fieldErrors.x)` (`src/errors/apiError.ts`).

Fonctionnement, et comment ajouter un texte, un code d'erreur ou une langue : [guide i18n](../docs/technical/i18n.fr.md).

---

## 10. Composants d'interface

Le style utilise **Tailwind CSS v4** (classes utilitaires dans `className`) et les composants viennent de **shadcn/ui** : la CLI copie leur code dans `src/components/ui/`, bâti sur les primitives Radix (clavier, focus, ARIA). Ce code appartient au projet et se modifie.

Plus précisément, ils sont tirés du registre shadcn/ui, style **`radix-nova`** (base Radix, preset Nova), enregistré dans `components.json` : la CLI réutilise ce style à chaque `add`, pour que les nouveaux composants ressemblent aux existants. Catalogue, exemples et props de chaque composant : [ui.shadcn.com/docs/components](https://ui.shadcn.com/docs/components).

| Action                                 | Commande / fichier                                                                                            |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Ajouter un composant                   | `pnpm dlx shadcn@latest add <nom>` (ex. `dialog`), puis le relire                                             |
| Voir ce que changerait une mise à jour | `pnpm dlx shadcn@latest add <nom> --diff`                                                                     |
| Mettre à jour un composant             | `pnpm dlx shadcn@latest add <nom> --overwrite`, puis relire le diff git et remettre les modifications locales |
| Modifier le thème                      | Variables CSS de `src/index.css` (`:root`, `.dark`)                                                           |
| Fusionner des classes selon un état    | `cn()` (`import { cn } from 'cn'`)                                                                            |

- N'ajouter que les composants réellement utilisés. Ils vont dans `src/components/ui/` ; les composants métier (qui appellent `t()` et les hooks d'API) restent dans `src/components/`.
- L'alias `@/` (`@/` → `src/`) sert à la CLI, via les `aliases` de `components.json`, pour savoir où écrire les fichiers et comment les importer ; il est configuré dans `tsconfig.json`, `tsconfig.app.json` et `vite.config.ts`. Les composants générés importent `cn` et `radix-ui` directement ; le reste du code garde des imports relatifs.
- `--overwrite` remplace entièrement le fichier : les modifications locales d'un composant de `ui/` sont perdues si on ne les remet pas depuis le diff git. Garder ces modifications légères.
- ESLint : `react-refresh/only-export-components` est désactivée pour `src/components/ui/` (`eslint.config.js`), car les composants shadcn exportent aussi leurs variantes (ex. `buttonVariants`) ; cela les garde proches de la version générée.
- Aucun texte n'est écrit dans un composant de `ui/` : il les reçoit en props ou en enfants, traduits avec `t()`.
- Le dialogue de suppression du compte garde le `<dialog>` natif (focus piégé et Échap gérés par le navigateur), mis en forme avec Tailwind.

### Mode sombre

- Trois préférences, choisies avec le sélecteur de thème de l'en-tête : **Système** (par défaut, suit le thème du système d'exploitation, en direct), **Clair** et **Sombre**. Le choix est mémorisé dans `localStorage` (`tierlist.theme`), par navigateur.
- `src/theme/index.ts` pose la classe `dark` sur `<html>` (ou la retire). Les couleurs viennent alors du bloc `.dark` de `src/index.css` : les composants qui utilisent les jetons du thème (`bg-background`, `text-muted-foreground`, `border-input`…) n'ont rien à faire de plus. Pour un cas particulier, la variante `dark:` de Tailwind s'applique (ex. `dark:bg-input/30`).
- Un petit script inline dans `index.html` applique le thème avant le chargement de l'application, pour éviter un flash clair en mode sombre. Il reprend la clé de stockage : la garder égale à `THEME_STORAGE_KEY` (`src/constants/theme.ts`). Un petit `<style>` inline donne tout de suite à `html.dark` son fond sombre, car en développement Vite injecte `index.css` par JavaScript, après le premier affichage : garder sa couleur égale à `--background` du bloc `.dark`.
- `color-scheme: dark` passe aussi les éléments natifs (barres de défilement, `<select>`, autocomplétion) en sombre.
