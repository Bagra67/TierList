# TierList — Frontend

English | [Français](README.fr.md)

**React 19 + TypeScript** frontend, built with **Vite**, the TierList web interface (accounts, sign-in, email confirmation, password reset). Tooling:

- **ESLint + Prettier** for automatic linting and formatting;
- **pnpm** as the package manager.

> This folder is part of the [TierList](../README.md) repository. **All commands below are run from the `frontend/` folder** (`cd frontend`).

---

## 1. Prerequisites

- **Node.js 26** (version pinned in `.nvmrc` at the repository root): `node --version`
- **pnpm**: `npm install -g pnpm`, then `pnpm --version`. The exact version is pinned in the `packageManager` field of `package.json` and locked in `pnpm-lock.yaml`.

---

## 2. Installing the project

```bash
pnpm install
```

Installs the dependencies at the exact versions of `pnpm-lock.yaml` and enables the git hook (husky) through the `prepare` script.

---

## 3. Running the project

| Action                        | Command                            |
| ----------------------------- | ---------------------------------- |
| Dev server (hot reload)       | `pnpm dev` → http://localhost:5173 |
| Production build (in `dist/`) | `pnpm build`                       |
| Preview the build             | `pnpm preview`                     |
| Check TypeScript types        | `pnpm typecheck`                   |
| Run the tests (Vitest)        | `pnpm test`                        |
| Tests in watch mode           | `pnpm test:watch`                  |
| Tests with coverage           | `pnpm test:coverage`               |

For the message to show up, also run the backend in another terminal (`cd backend` then `uv run fastapi dev app/main.py`).
Calls to `/api/...` are forwarded unchanged to `http://127.0.0.1:8000/api/...` by the proxy configured in `vite.config.ts`: the backend serves its API under `/api`, as in production, where FastAPI also serves the build ([deployment guide](../docs/technical/deployment.md)).

Tests use **Vitest** (jsdom) and **Testing Library**, configured in the `test` block of `vite.config.ts`. Test files sit next to the code (`*.test.tsx`), and `fetch` is stubbed (`vi.stubGlobal`) so tests never call the backend. CI runs `pnpm test:coverage`. Details of each test: [testing guide](../docs/technical/testing.md).

---

## 4. Managing packages

> ⚠️ Always use `pnpm` (not `npm install` or `yarn`) to keep `pnpm-lock.yaml` consistent.

| Action                             | Command                                                     |
| ---------------------------------- | ----------------------------------------------------------- |
| Add a package                      | `pnpm add <package>` (e.g. `pnpm add react-router`)         |
| Add a specific version             | `pnpm add <package>@<version>` (e.g. `pnpm add dayjs@1.11`) |
| Add a dev package                  | `pnpm add -D <package>` (e.g. `pnpm add -D vitest`)         |
| Remove a package                   | `pnpm remove <package>`                                     |
| Update a package                   | `pnpm update <package>`                                     |
| Update to the latest major version | `pnpm update <package> --latest`                            |
| Show outdated packages             | `pnpm outdated`                                             |
| List installed packages            | `pnpm list`                                                 |
| Run an installed binary            | `pnpm exec <command>`                                       |

---

## 5. Lint and formatting

| Action                               | Command             |
| ------------------------------------ | ------------------- |
| Analyze the code (ESLint)            | `pnpm lint`         |
| Fix automatically                    | `pnpm lint:fix`     |
| Format all the code (Prettier)       | `pnpm format`       |
| Check formatting without changing it | `pnpm format:check` |
| Find unused exports, files and deps  | `pnpm knip`         |

It happens automatically in two places:

- **On save in VS Code**: Prettier formatting + ESLint fixes. Install the recommended extensions (VS Code suggests them when opening the `TierList` folder): ESLint and Prettier.
- **Before each commit**: the husky hook runs `lint-staged`, which fixes and formats the modified files. If an ESLint error cannot be fixed automatically, the commit is blocked.

ESLint also checks **accessibility** with `eslint-plugin-jsx-a11y-x` (`recommended` rules): text alternatives (`alt`), labels, valid ARIA roles and attributes, keyboard support of clickable elements. It is the maintained fork of `eslint-plugin-jsx-a11y`, with the same rules, chosen because the original does not support ESLint 10. It finds what can be seen in the code; focus, contrast and screen reader behavior still need a check in the browser.

**knip** lists what nothing uses: exports, files and dependencies (`knip.jsonc`: `schema.d.ts` and the shadcn exports of `src/components/ui/` are ignored, `git-cliff` is run by `scripts/prepare-release.sh`). It runs on CI: remove what it reports, or explain an exception in `knip.jsonc`.

**Where to put a type or an interface**:

- used by **one file only** (component props, internal types): it stays in that file, **without `export`**. TypeScript then forbids any other file from using it.
- needed by **a second file**: export it from the module that owns it (e.g. `src/api/<resource>.ts` for API types, which come from `schema.d.ts`) and import it from there.
- `pnpm typecheck` blocks the use of a type that is not exported, and `pnpm knip` reports an export nobody imports. A type copied instead of imported is the only case left to review.

Configuration: `eslint.config.js`, `.prettierrc`, `.prettierignore`, `lint-staged` section of `package.json`.

`pnpm format` and `pnpm format:check` also cover the repository's `docs/` folder, with the same `.prettierrc` (CI checks it too). The pre-commit hook does not format `docs/`: run `pnpm format` before committing a doc change.

---

## 6. Project structure

```
frontend/
├── public/                 # Static files served as is (favicon…)
├── src/
│   ├── api/
│   │   ├── client.ts       # Shared HTTP client (openapi-fetch), access token + refresh middleware
│   │   ├── queryClient.ts  # TanStack Query setup (retry, error logging)
│   │   ├── auth.ts         # /auth calls + useCurrentUser, useLogin, useRegister, useLogout hooks
│   │   ├── templates.ts    # /templates calls + useTemplates, useTemplate, useCreateTemplate, useDeleteTemplate hooks
│   │   ├── *.test.ts       # Tests of the API layer
│   │   └── schema.d.ts     # API types generated from backend/openapi.json (do not edit)
│   ├── auth/               # Route guards: RequireAuth (private pages → /login), RedirectIfSignedIn (/login, /register → back where the user was going)
│   ├── components/         # Reusable components (Layout, Logo, AuthPageShell, ErrorMessage, EmptyState, ErrorBoundary, SettingsPanel, LogoutButton, LanguageSwitcher, ThemeSwitcher, TextField, DeleteAccountDialog, GoogleSignInLink, EmailVerificationBanner, MainNav, ModalDialog, CreateTemplateDialog, DeleteTemplateDialog, TemplateNameField, TierEditor, TileEditor, InlineEditField, ColorField, SortableList, GameScreen, GameBoard, gameBoardParts, CooldownBoard, EndCooldownDialog, GameAdminControls, PlacedList, Countdown, GameItemView)
│   │   └── ui/             # shadcn/ui components (button, input, label, card, popover), editable
│   ├── constants/          # Fixed values: auth.ts, routes.ts, http.ts, i18n.ts, templates.ts, theme.ts, brand.ts
│   ├── errors/             # ApiError, getFieldErrors, error code translation (+ tests)
│   ├── i18n/               # Translations: setup, locales/fr.ts and en.ts (+ tests)
│   ├── theme/              # Dark mode: theme preference, dark class on <html>; WCAG contrast (+ tests)
│   ├── pages/              # One component per route (HomePage, LoginPage, RegisterPage, VerifyEmailPage, ForgotPasswordPage, ResetPasswordPage, TemplatesPage, TemplateEditorPage) + tests
│   ├── test/
│   │   ├── setup.ts        # Test setup (jest-dom matchers, cleanup, French by default)
│   │   ├── renderWithQueryClient.tsx # render() inside a fresh QueryClient
│   │   ├── matchMedia.ts   # Fake matchMedia: light / dark system theme
│   │   └── stubBackend.ts  # Fake backend replacing fetch, route by route
│   ├── App.tsx             # Routes (react-router), inside the shared Layout
│   ├── App.test.tsx        # Routing tests: redirection, session restore, logout
│   ├── index.css           # Tailwind CSS + shadcn/ui theme (colors, radius, font)
│   └── main.tsx            # React entry point
├── components.json         # shadcn/ui CLI config (style, aliases)
├── index.html              # HTML page + script applying the theme before the app loads
├── eslint.config.js
├── vite.config.ts          # Vite config (React, Tailwind CSS, @/ alias) + /api proxy + Vitest config
└── package.json
```

---

## 7. API types (generated)

API types are **never written by hand**: `src/api/schema.d.ts` is generated by `pnpm gen:api` from `backend/openapi.json`, the contract exported by the backend. Use them through `components['schemas'][...]`, as in `src/api/auth.ts`:

```ts
import type { components } from './schema';

export type User = components['schemas']['UserResponse'];
```

A backend change that breaks the frontend then becomes a `pnpm typecheck` error.

When you add or change a route or a Pydantic schema:

1. `uv run python scripts/export_openapi.py` (in `backend/`) updates `openapi.json`;
2. `pnpm gen:api` (in `frontend/`) regenerates the TypeScript types;
3. fix any `pnpm typecheck` error: it shows the frontend code affected by the change;
4. commit `backend/openapi.json` and `frontend/src/api/schema.d.ts` together.

If you forget step 1, the backend test `test_openapi_schema_is_up_to_date` fails; if you forget step 2, the CI step "Check API types are up to date" fails.

---

## 8. Data fetching

Server data goes through **TanStack Query** on top of a shared **openapi-fetch** client. Components never call `fetch` or `useEffect` to load data:

```
Component → useX() hook (TanStack Query) → getX() → apiClient (openapi-fetch) → /api → FastAPI
```

- `src/api/client.ts`: `apiClient`, the only HTTP client. Its paths, parameters and responses are typed by `schema.d.ts`, so a wrong path or field is a `pnpm typecheck` error. `ApiError` (`src/errors/apiError.ts`: `status`, `body`, the API `code` and `params`, and the backend `detail` as `message`) is thrown for any non-2xx response. Components display `translateError(t, error)`, never `error.message`. Fixed values (routes, HTTP statuses, limits) come from `src/constants/`.
- `src/api/queryClient.ts`: `createQueryClient()`, used by `main.tsx`. It retries a failed query once and logs every failure to the console, in one place.
- TanStack Query handles loading and error states, cancellation on unmount, caching (the same `queryKey` is fetched once) and refetching.

To add an endpoint, create `src/api/<resource>.ts` following `auth.ts`, e.g. a read:

```ts
export async function getMe(signal?: AbortSignal): Promise<User> {
  return dataOrThrow(await apiClient.GET('/auth/me', { signal }));
}

export function useMe() {
  return useQuery({ queryKey: ['me'], queryFn: ({ signal }) => getMe(signal) });
}
```

`dataOrThrow` (`src/api/client.ts`) returns the body of a successful response and throws `ApiError` otherwise; `throwIfError` does the same for responses without a body (`204`). The component then only reads the state: `const { data, isPending, isError } = useMe();`.

In tests, render components with `renderWithQueryClient` (`src/test/`) and stub `fetch` with `stubBackend`, as in `App.test.tsx`.

### Authenticated requests

`apiClient` adds the access token (kept in memory) to every request. When a request gets a `401`, it refreshes the token once through `POST /auth/refresh` (refresh cookie) and retries the request; concurrent requests share the same refresh. Nothing to do in a new `api/<resource>.ts`. The current user is read with `useCurrentUser()`, and private pages are placed under the `RequireAuth` route in `App.tsx`. Details: [authentication guide](../docs/technical/authentication.md).

---

## 9. Translations

Every displayed text goes through `t()` from `react-i18next`, and the interface is available in French and English (language switcher in the settings panel, opened by the gear of the header on every page):

```tsx
const { t } = useTranslation();
return <h1>{t('auth.login.title')}</h1>;
```

- Texts live in `src/i18n/locales/fr.ts` (reference) and `en.ts`; a missing or extra key in `en.ts` is a `pnpm typecheck` error, and `t('…')` keys are type-checked too.
- API errors are translated from their code: `translateError(t, error)` and `translateFieldError(t, fieldErrors.x)` (`src/errors/apiError.ts`).

How it works and how to add a text, an error code or a language: [i18n guide](../docs/technical/i18n.md).

---

## 10. UI components

Styling uses **Tailwind CSS v4** (utility classes in `className`) and the components come from **shadcn/ui**: the CLI copies their code into `src/components/ui/`, built on Radix primitives (keyboard, focus, ARIA). The code belongs to the project and can be edited.

More precisely, they are taken from the shadcn/ui registry, style **`radix-nova`** (Radix base, Nova preset), recorded in `components.json`: the CLI reuses this style on every `add`, so new components match the existing ones. Catalog, examples and props of each component: [ui.shadcn.com/docs/components](https://ui.shadcn.com/docs/components).

| Action                      | Command / file                                                                                       |
| --------------------------- | ---------------------------------------------------------------------------------------------------- |
| Add a component             | `pnpm dlx shadcn@latest add <name>` (e.g. `dialog`), then review it                                  |
| See what an update changes  | `pnpm dlx shadcn@latest add <name> --diff`                                                           |
| Update a component          | `pnpm dlx shadcn@latest add <name> --overwrite`, then review the git diff and put local changes back |
| Change the theme            | CSS variables in `src/index.css` (`:root`, `.dark`)                                                  |
| Merge classes conditionally | `cn()` (`import { cn } from 'cn'`)                                                                   |

- Only add the components actually used. They go into `src/components/ui/`; business components (which call `t()` and the API hooks) stay in `src/components/`.
- The `@/` alias (`@/` → `src/`) is used by the CLI, through the `aliases` of `components.json`, to know where to write files and how to import them; it is configured in `tsconfig.json`, `tsconfig.app.json` and `vite.config.ts`. The generated components import `cn` and `radix-ui` directly; the rest of the code keeps relative imports.
- `--overwrite` replaces the file entirely: local changes to a `ui/` component are lost unless put back from the git diff. Keep such changes small.
- ESLint: `react-refresh/only-export-components` is off for `src/components/ui/` (`eslint.config.js`), since shadcn components also export their variants (e.g. `buttonVariants`); this keeps them close to the generated version.
- Texts are never written in a `ui/` component: they receive them as props or children, translated with `t()`.
- Drop-down lists use `NativeSelect` (`src/components/ui/native-select.tsx`): a native `<select>` with the look of the fields (border, focus, dark mode), whose keyboard, mobile and screen reader behavior comes from the browser. Native checkboxes get the accent color and a visible focus ring from the base styles of `src/index.css`.
- Links inside text use `textLinkClassName` (`src/components/ui/text-link.ts`): always underlined, so they do not rely on color alone (WCAG 1.4.1). Navigation links (header, footer, list titles) keep their own style.
- When the system asks for reduced motion, `src/index.css` makes animations and transitions near-instant (popover opening…). The spinner (`animate-spin`) keeps turning: stopped, it would look like a broken circle instead of saying "in progress".
- The dialogs keep the native `<dialog>` (focus trap and Escape handled by the browser), styled with Tailwind; `ModalDialog` holds the shell (title, styling) and `DialogActions` the Cancel / submit footer, shared by every dialog. `cn()` comes straight from the `cn` package, like in the shadcn/ui components.
- Drag and drop (template editor) uses **dnd-kit** (`@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities`), wrapped in `SortableList`: neither Radix nor shadcn/ui offers a sortable list, and dnd-kit handles the mouse, touch and the keyboard (Space, arrows, Escape) with screen reader announcements, translated through `templates.editor.dnd.*`.
- The tier color picker (`ColorField`) uses **react-colorful** (`HexColorPicker`, `HexColorInput`) in a shadcn `popover`: a small library without dependencies, whose sliders work with the keyboard. Its accessibility labels are written in English in the library: `ColorField` replaces them with the translations (`templates.editor.color.*`) after each render.

### Visual identity

- The palette (named "Le Plateau": a game show where everyone ranks together) lives in the `:root` (light) and `.dark` blocks of `src/index.css`, as shadcn/ui tokens: indigo ink text (`--foreground`) on a cool off-white stage (`--background`), raspberry accent for the main actions (`--primary`), brick red for errors and destructive actions (`--destructive`, a hue kept apart from the raspberry so that an error never looks like the accent), and `--success` for positive states (e.g. an online player).
- The token pairs used for text are chosen for WCAG contrast: text at least 4.5:1, field borders (`--input`) and the focus ring (`--ring`) at least 3:1. A translucent variant (`bg-primary/90`, `bg-destructive/10`…) lowers the contrast: check it too, and check every pair again when changing a color.
- The focus ring uses `--ring` at full opacity (`ring-ring`, `outline-ring`), never a faded version, so that keyboard focus stays visible.
- Two typefaces, self-hosted with Fontsource (no third-party font service): **Geist** for the text (`font-sans`) and **Anybody** for the headings (`font-heading`, applied to `h1` and `h2`; the small `h3` section labels stay in Geist). Anybody has a variable width (`font-stretch`, 50% to 150%), used wide for the logo, the tier letters and the countdown.
- On the game board, the cooldown and the results, each tier starts with a **letter block**: its name in Anybody on the tier color (`TierLabel`). The text is ink or white, whichever contrasts most with the color chosen by the owner (`readableTextColor`, `src/theme/contrast.ts`); on a few mid-tone colors neither reaches 4.5:1, which the large letters (S, A+…) do not need. A long name is cut after three lines, shown in full by its tooltip and read in full by screen readers. The tier rows do not clip their content (no `overflow-hidden`), so that a dragged item stays visible when it leaves its row. Items share a single chip style (`ITEM_CHIP_CLASS`, `src/components/boardStyles.ts`), 56 px high on mobile and 64 px from `sm`. The item being dragged gets the `shadow-lift` shadow, and the keyboard focus a ring distinct from the accent border of the current item.
- States: `ErrorMessage` shows an error on a light destructive background (`role="alert"`); an empty list uses `EmptyState` (a dashed box that says what to do, with the action when it is not already next to the page title); a warning uses `--warning` as a border and a light background, never as text color (yellow text would be unreadable).
- The logo (`Logo`, in the header) and `public/favicon.svg` are three stacked bars in the colors of the S, A and B tiers (`LOGO_BARS`, `src/constants/brand.ts`). The `theme-color` meta tags of `index.html` repeat `--background` of each theme for the first paint, then `applyTheme` gives them the color of the theme chosen in the application (`THEME_COLORS`, `src/constants/theme.ts`): keep the three equal.

### Dark mode

- Three preferences, chosen with the theme switcher of the settings panel (gear of the header): **System** (default, follows the operating system theme, live), **Light** and **Dark**. The choice is stored in `localStorage` (`tierlist.theme`), per browser.
- `src/theme/index.ts` puts the `dark` class on `<html>` (or removes it). The colors then come from the `.dark` block of `src/index.css`: components using the theme tokens (`bg-background`, `text-muted-foreground`, `border-input`…) need nothing more. For a specific case, Tailwind's `dark:` variant applies (e.g. `dark:bg-input/30`).
- A small inline script in `index.html` applies the theme before the application loads, to avoid a light flash in dark mode. It repeats the storage key: keep it equal to `THEME_STORAGE_KEY` (`src/constants/theme.ts`). A small inline `<style>` gives `html.dark` its dark background right away, since in development Vite injects `index.css` through JavaScript, after the first paint: keep its color equal to `--background` of the `.dark` block.
- `color-scheme: dark` turns native elements (scrollbars, `<select>`, autofill) dark too.
