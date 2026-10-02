# TierList — Frontend

English | [Français](README.fr.md)

**React 19 + TypeScript** frontend, built with **Vite**, which displays the message returned by the backend's `GET /hello`. Tooling:

- **ESLint + Prettier** for automatic linting and formatting;
- **pnpm** as the package manager.

> This folder is part of the [TierList](../README.md) repository. **All commands below are run from the `frontend/` folder** (`cd frontend`).

---

## 1. Prerequisites

- **Node.js 24 LTS** (version pinned in `.nvmrc` at the repository root): `node --version`
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
Calls to `/api/...` are forwarded to `http://127.0.0.1:8000/...` by the proxy configured in `vite.config.ts`.

Tests use **Vitest** (jsdom) and **Testing Library**, configured in the `test` block of `vite.config.ts`. Test files sit next to the code (`*.test.tsx`), and the API module is mocked so tests never call the backend. CI runs `pnpm test:coverage`. Details of each test: [testing guide](../docs/testing.md).

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

It happens automatically in two places:

- **On save in VS Code**: Prettier formatting + ESLint fixes. Install the recommended extensions (VS Code suggests them when opening the `TierList` folder): ESLint and Prettier.
- **Before each commit**: the husky hook runs `lint-staged`, which fixes and formats the modified files. If an ESLint error cannot be fixed automatically, the commit is blocked.

Configuration: `eslint.config.js`, `.prettierrc`, `.prettierignore`, `lint-staged` section of `package.json`.

---

## 6. Project structure

```
frontend/
├── public/                 # Static files served as is (favicon…)
├── src/
│   ├── api/
│   │   ├── hello.ts        # GET /api/hello call to the FastAPI backend
│   │   └── schema.d.ts     # API types generated from backend/openapi.json (do not edit)
│   ├── test/
│   │   └── setup.ts        # Test setup (jest-dom matchers, cleanup)
│   ├── App.tsx             # Displays the backend message
│   ├── App.test.tsx        # App tests: loading, message, error
│   └── main.tsx            # React entry point
├── eslint.config.js
├── vite.config.ts          # Vite config + /api proxy + Vitest config
└── package.json
```

---

## 7. API types (generated)

API types are **never written by hand**: `src/api/schema.d.ts` is generated by `pnpm gen:api` from `backend/openapi.json`, the contract exported by the backend. Use them through `components['schemas'][...]`, as in `src/api/hello.ts`:

```ts
import type { components } from './schema';

export type HelloResponse = components['schemas']['HelloResponse'];
```

A backend change that breaks the frontend then becomes a `pnpm typecheck` error.

When you add or change a route or a Pydantic schema:

1. `uv run python scripts/export_openapi.py` (in `backend/`) updates `openapi.json`;
2. `pnpm gen:api` (in `frontend/`) regenerates the TypeScript types;
3. fix any `pnpm typecheck` error: it shows the frontend code affected by the change;
4. commit `backend/openapi.json` and `frontend/src/api/schema.d.ts` together.

If you forget step 1, the backend test `test_openapi_schema_is_up_to_date` fails; if you forget step 2, the CI step "Check API types are up to date" fails.
