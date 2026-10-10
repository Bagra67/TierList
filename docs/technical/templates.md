# Templates

English | [Français](templates.fr.md)

How templates are stored and exposed by the API: data model, endpoints, soft deletion and purge, and where it lives in the code. What a template is for the user: [product](../product/product.md).

## 1. Functional overview

A template is what gets ranked: its **tiers** (the rows of the tier list) and its **tiles** (the items to rank). It is **private** to its owner.

| Action            | Endpoint                 | Result                                                                                                      |
| ----------------- | ------------------------ | ----------------------------------------------------------------------------------------------------------- |
| Create a template | `POST /templates`        | A template with the six default tiers (S to E) and no tile.                                                 |
| List my templates | `GET /templates`         | My active templates, with their number of tiles, the most recently modified first.                          |
| Open a template   | `GET /templates/{id}`    | The template, its tiers and its tiles, sorted by position.                                                  |
| Rename a template | `PATCH /templates/{id}`  | The new name; the last modification date is updated.                                                        |
| Delete a template | `DELETE /templates/{id}` | The template disappears for its owner at once, and is erased permanently after the retention period (§2.3). |

On the frontend, the _My templates_ page lists, creates and deletes templates; opening one shows its tiers, read-only until the editor comes (#79, #80). See §3.

### Rules

- **Name**: 1 to 100 characters, surrounding spaces removed (a name made only of spaces is empty, hence refused with a `422`).
- **Default tiers**, from top to bottom: `S` `#FF7F7F`, `A` `#FFBF7F`, `B` `#FFDF7F`, `C` `#FFFF7F`, `D` `#BFFF7F`, `E` `#7FFF7F` (`DEFAULT_TIERS`, `app/constants/templates.py`).
- **Last modification** (`updated_at`): changes when the template changes, and must also change when one of its tiers or tiles changes: the service updates it explicitly (§2.2). It is the date shown to the user and the order of the list.
- **Privacy**: a template of another user answers `404`, exactly like an unknown or deleted one: the API never reveals that it exists.
- **Account deletion** erases the user's templates, deleted ones included.

### Messages

The API returns an error **code**; the frontend translates it (`errors.api.*` in `frontend/src/i18n/locales/`).

| Situation                                    | HTTP | API code             | Translation (FR / EN)                                                                       |
| -------------------------------------------- | ---- | -------------------- | ------------------------------------------------------------------------------------------- |
| Template unknown, deleted or of another user | 404  | `template_not_found` | `Ce template est introuvable.` / `This template could not be found.`                        |
| Invalid name (empty, too long)               | 422  | `validation_error`   | `Certains champs sont invalides.` / `Some fields are invalid.`, plus the error of the field |
| Missing or invalid access token              | 401  | `not_authenticated`  | Handled by the API client: refresh of the session, otherwise back to `/login`               |

## 2. Technical design

### 2.1 Data model

```
users ──< templates ──< tiers
              │
              └──────< tiles
```

| Table       | Columns                                                                                          | Notes                                                          |
| ----------- | ------------------------------------------------------------------------------------------------ | -------------------------------------------------------------- |
| `templates` | `id`, `owner_id` → `users`, `name` (100), `created_at`, `updated_at`, `deleted_at`               | `ON DELETE CASCADE` towards `users`; index on `owner_id`.      |
| `tiers`     | `id`, `template_id` → `templates`, `name` (50), `color` (`#RRGGBB`), `position`, dates           | `ON DELETE CASCADE` towards `templates`; `position` 0 = top.   |
| `tiles`     | `id`, `template_id` → `templates`, `text` (200, empty for an image-only tile), `position`, dates | `ON DELETE CASCADE` towards `templates`; `position` 0 = first. |

`position` has **no unique constraint**: reordering would break it while the other rows are being shifted. The service keeps positions continuous.

### 2.2 Model mixins

The common columns are shared through SQLAlchemy mixins (`app/db/mixins.py`). Each model takes only the ones it needs:

| Mixin                 | Columns                    | Used by                    |
| --------------------- | -------------------------- | -------------------------- |
| `UUIDPrimaryKeyMixin` | `id` (UUID v4)             | `Template`, `Tier`, `Tile` |
| `TimestampMixin`      | `created_at`, `updated_at` | `Template`, `Tier`, `Tile` |
| `SoftDeleteMixin`     | `deleted_at` (nullable)    | `Template`                 |

- The dates are set by PostgreSQL with `clock_timestamp()`, not `now()`: `now()` is the start of the transaction, the same for every write of one transaction.
- `onupdate` only sees an `UPDATE` of the row itself: when a tier or a tile changes, the service must update the template's `updated_at` explicitly.
- `SoftDeleteMixin` is not put everywhere on purpose: a soft-deleted table forces every query to filter `deleted_at`.

### 2.3 Soft deletion and purge

`DELETE /templates/{id}` only sets `deleted_at`. Every query of the repository filters `deleted_at IS NULL`, so the template disappears at once for its owner (`404`, absent from the list).

The command `scripts/purge_deleted_templates.py` then erases permanently the templates deleted more than `DELETED_TEMPLATE_RETENTION_DAYS` days ago; their tiers and tiles go with them (`ON DELETE CASCADE`). It logs and prints the number of templates purged, and can be run again safely: it only removes what has expired.

```bash
# in backend/
uv run python scripts/purge_deleted_templates.py
```

It must be scheduled once a day on the server (cron or the host's scheduled task): see the [TODO](../../TODO.md). Without it, deleted templates stay in the database.

### 2.4 Settings

| Variable                          | Purpose                                                           | Default |
| --------------------------------- | ----------------------------------------------------------------- | ------- |
| `DELETED_TEMPLATE_RETENTION_DAYS` | Days a deleted template stays in the database before being purged | `30`    |

### 2.5 Endpoints

Every route requires the Bearer access token (`401` otherwise).

| Method and path          | Body     | Success                      | Errors              |
| ------------------------ | -------- | ---------------------------- | ------------------- |
| `POST /templates`        | `{name}` | `201` `TemplateResponse`     | `401`, `422`        |
| `GET /templates`         | —        | `200` `TemplateListResponse` | `401`               |
| `GET /templates/{id}`    | —        | `200` `TemplateResponse`     | `401`, `404`        |
| `PATCH /templates/{id}`  | `{name}` | `200` `TemplateResponse`     | `401`, `404`, `422` |
| `DELETE /templates/{id}` | —        | `204`                        | `401`, `404`        |

- `TemplateResponse` is `{id, name, created_at, updated_at, tiers: [{id, name, color, position}], tiles: [{id, text, position}]}`, tiers and tiles sorted by `position`.
- `TemplateListResponse` is `{items: [{id, name, tile_count, updated_at}]}`. An object rather than an array, so that pagination (#105) can add a field without breaking the contract. The list is read in **one query**: the database counts the tiles (no N+1).

### 2.6 Known limitations

- No pagination of the list yet (#105).
- No super admin view of deleted templates yet (#104).
- Tiers and tiles cannot be edited through the API yet: only the default tiers exist, and no tile.

## 3. In the code

### Backend (`backend/app/`)

| Layer         | File                                                                          | Content                                                                                                                              |
| ------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Routes        | `api/routes/templates.py`                                                     | The five `/templates` routes; map `TemplateNotFoundError` to a `404` `template_not_found`.                                           |
| Dependencies  | `api/dependencies.py`, `api/responses.py`                                     | `get_template_service`; `UNAUTHORIZED_RESPONSE`, the `401` documented in OpenAPI, shared with the `/auth` routes.                    |
| Schemas       | `schemas/templates.py`                                                        | `CreateTemplateRequest`, `RenameTemplateRequest` (shared `TemplateName` rule), `TemplateResponse`, `TemplateListResponse`.           |
| Service       | `services/templates.py`                                                       | `TemplateService`: create with the default tiers, list, get, rename, soft delete, `purge_deleted`. Owns the transactions (`commit`). |
| Repository    | `repositories/templates.py`                                                   | Queries only: active template of an owner (with tiers and tiles), list with tile count, purge.                                       |
| Models        | `models/template.py`, `models/tier.py`, `models/tile.py`, `db/mixins.py`      | One file per class; the mixins of §2.2.                                                                                              |
| Exceptions    | `exceptions/templates.py`                                                     | `TemplateNotFoundError`.                                                                                                             |
| Constants     | `constants/templates.py`, `constants/error_codes.py`, `constants/messages.py` | Lengths tied to the schema, `DEFAULT_TIERS`, `TEMPLATE_NOT_FOUND` code and developer message.                                        |
| Configuration | `core/config.py`                                                              | `DELETED_TEMPLATE_RETENTION_DAYS`.                                                                                                   |
| Migration     | `migrations/versions/855df2a2ea2b_create_templates_tiers_and_tiles.py`        | Creates the three tables.                                                                                                            |
| Command       | `scripts/purge_deleted_templates.py` (in `backend/`)                          | Purge of §2.3.                                                                                                                       |

### Frontend (`frontend/src/`)

| Layer        | File                                            | Content                                                                                                                                           |
| ------------ | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| API          | `api/templates.ts`                              | One function per endpoint used (list, get, create, delete) and the hooks `useTemplates`, `useTemplate`, `useCreateTemplate`, `useDeleteTemplate`. |
| Constants    | `constants/templates.ts`, `constants/routes.ts` | `TEMPLATE_NAME_MAX_LENGTH` (equal to the backend), the query keys; `ROUTES.TEMPLATES`, `ROUTES.TEMPLATE_EDITOR` and `templateEditorPath(id)`.     |
| Pages        | `pages/TemplatesPage.tsx`                       | _My templates_ (`/templates`): name, number of tiles and last modification date of each template, empty state, loading and error states.          |
|              | `pages/TemplateEditorPage.tsx`                  | `/templates/:templateId`: name and tiers of the template, read-only for now; the editing of tiers (#79) and tiles (#80) comes here.               |
| Components   | `components/CreateTemplateDialog.tsx`           | Native `<dialog>`: required name, error of the field from the `422`, then opens the new template.                                                 |
|              | `components/DeleteTemplateDialog.tsx`           | Native `<dialog>` of confirmation; the list is refreshed after the deletion.                                                                      |
| Navigation   | `components/MainNav.tsx` (in `Layout.tsx`)      | Links _Home_ and _My templates_ in the header, shown once signed in.                                                                              |
| Translations | `i18n/locales/fr.ts`, `en.ts`                   | `nav.*`, `templates.*` (number of tiles with plural forms, date formatted in the language of the interface) and `errors.api.template_not_found`.  |

Every change invalidates the `['templates']` cache: the list and the opened templates are read again.

### Tests

`backend/tests/integration/test_templates.py` (endpoints) and `test_template_purge.py` (purge), against a real PostgreSQL; `frontend/src/pages/TemplatesPage.test.tsx` and `TemplateEditorPage.test.tsx` for the screens. All are described in the [testing guide](testing.md).
