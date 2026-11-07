---
name: api-sync
description: Regenerate backend/openapi.json and the frontend API types (frontend/src/api/schema.d.ts) after a change to a FastAPI route or a Pydantic schema, then check they changed together. Use whenever an API contract changes (AGENTS.md §23).
---

# API sync

Frontend API types are never written by hand: they are generated from the backend OpenAPI schema.
Both generated files are protected by a hook, so this is the only way to update them.

## Steps

1. Export the OpenAPI schema, from `backend/`:

   ```bash
   uv run python scripts/export_openapi.py
   ```

2. Generate the TypeScript types, from `frontend/`:

   ```bash
   pnpm gen:api
   ```

3. Check what changed:

   ```bash
   git status --short -- backend/openapi.json frontend/src/api/schema.d.ts
   git diff --stat -- backend/openapi.json frontend/src/api/schema.d.ts
   ```

   - Both changed: expected after a contract change.
   - Neither changed: the contract is unchanged, nothing to commit.
   - Only one changed: report it, it means the other was out of date before this change.

4. Run `pnpm typecheck` in `frontend/`. A failure shows the frontend code that uses the old contract:
   list those places and fix them as part of the task.

5. Remind that `backend/openapi.json` and `frontend/src/api/schema.d.ts` are committed together, in
   the same commit as the contract change. The backend `test_openapi.py` and the CI step "Check API
   types are up to date" fail otherwise.

## Report

Give the endpoints and schemas whose contract changed (from the `openapi.json` diff), the result of
`pnpm typecheck`, and whether a breaking change needs the `!` marker and a `BREAKING CHANGE:` footer
(AGENTS.md §23, §40).
