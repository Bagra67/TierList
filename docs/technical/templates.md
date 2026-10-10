# Templates

English | [Français](templates.fr.md)

How templates are stored and exposed by the API: data model, endpoints, soft deletion and purge, and where it lives in the code. What a template is for the user: [product](../product/product.md).

## 1. Functional overview

A template is what gets ranked: its **tiers** (the rows of the tier list) and its **tiles** (the items to rank). It is **private** to its owner.

| Action            | Endpoint                                 | Result                                                                                                      |
| ----------------- | ---------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Create a template | `POST /templates`                        | A template with the six default tiers (S to E) and no tile.                                                 |
| List my templates | `GET /templates`                         | My active templates, with their number of tiles, the most recently modified first.                          |
| Open a template   | `GET /templates/{id}`                    | The template, its tiers and its tiles, sorted by position.                                                  |
| Rename a template | `PATCH /templates/{id}`                  | The new name; the last modification date is updated.                                                        |
| Add a tier        | `POST /templates/{id}/tiers`             | A tier at the bottom, named `?`, color `#BFBFBF`.                                                           |
| Change a tier     | `PATCH /templates/{id}/tiers/{tier_id}`  | Its name, its color and/or its position (the others are shifted).                                           |
| Delete a tier     | `DELETE /templates/{id}/tiers/{tier_id}` | The tier disappears, the others move up; refused for the last tier.                                         |
| Add a tile        | `POST /templates/{id}/tiles`             | A text tile at the end; refused beyond the maximum number of tiles.                                         |
| Change a tile     | `PATCH /templates/{id}/tiles/{tile_id}`  | Its text and/or its position in the template order.                                                         |
| Delete a tile     | `DELETE /templates/{id}/tiles/{tile_id}` | The tile disappears, the next ones move up.                                                                 |
| Delete a template | `DELETE /templates/{id}`                 | The template disappears for its owner at once, and is erased permanently after the retention period (§2.3). |

On the frontend, the _My templates_ page lists, creates and deletes templates; the editor renames the template and configures its tiers and its text tiles. See §3.

### Rules

- **Name**: 1 to 100 characters, surrounding spaces removed (a name made only of spaces is empty, hence refused with a `422`).
- **Default tiers**, from top to bottom: `S` `#FF7F7F`, `A` `#FFBF7F`, `B` `#FFDF7F`, `C` `#FFFF7F`, `D` `#BFFF7F`, `E` `#7FFF7F` (`DEFAULT_TIERS`, `app/constants/templates.py`).
- **Tiers**: name 1 to 50 characters (spaces removed), color `#RRGGBB` stored in upper case. A template keeps **at least one tier**: deleting the last one answers `409` `last_tier`.
- **Positions** of tiers start at 0 and stay continuous (no gap): moving or deleting a tier renumbers the others. A position past the end puts the tier last.
- **Empty update**: a `PATCH` without any field (or with only `null` values) changes nothing, not even the last modification date; the tier must still exist (`404` otherwise).
- The same goes for the tiles: an empty `PATCH` of a tile changes nothing.
- **Tiles**: text 1 to 200 characters (spaces removed). Without images (#81, see the [images guide](images.md)), a tile with no text would be empty, hence the `422`. The tiles follow the same position rules as the tiers: their order is the **template order**.
- **Tile limit** (free plan): **32 tiles** per template (`FREE_PLAN_MAX_TILES`), returned as `max_tiles` in `TemplateResponse` (property `Template.max_tiles`, which will depend on the owner's plan). Beyond it, `409` `tile_limit_reached` with the param `max_tiles`.
- **Simultaneous changes**: every change of the tiers or tiles locks the template row (`SELECT … FOR UPDATE`) until its commit. Two requests on the same template run one after the other, the second one seeing the result of the first: two simultaneous deletions cannot remove the last tier, two simultaneous additions cannot go beyond the tile limit.
- **Last modification** (`updated_at`): changes when the template changes, and must also change when one of its tiers or tiles changes: the service updates it explicitly (§2.2). It is the date shown to the user and the order of the list.
- **Privacy**: a template of another user answers `404`, exactly like an unknown or deleted one: the API never reveals that it exists.
- **Account deletion** erases the user's templates, deleted ones included.

### Messages

The API returns an error **code**; the frontend translates it (`errors.api.*` in `frontend/src/i18n/locales/`).

| Situation                                                         | HTTP | API code                                 | Translation (FR / EN)                                                                         |
| ----------------------------------------------------------------- | ---- | ---------------------------------------- | --------------------------------------------------------------------------------------------- |
| Template unknown, deleted or of another user                      | 404  | `template_not_found`                     | `Ce template est introuvable.` / `This template could not be found.`                          |
| Tier unknown in this template                                     | 404  | `tier_not_found`                         | `Ce tier est introuvable.` / `This tier could not be found.`                                  |
| Deleting the last tier                                            | 409  | `last_tier`                              | `Un template garde au moins un tier.` / `A template keeps at least one tier.`                 |
| Tile unknown in this template                                     | 404  | `tile_not_found`                         | `Cette tuile est introuvable.` / `This tile could not be found.`                              |
| Too many tiles                                                    | 409  | `tile_limit_reached` (param `max_tiles`) | `Un template a au plus {{max_tiles}} tuiles.` / `A template has at most {{max_tiles}} tiles.` |
| Invalid name, color or tile text (empty, too long, not `#RRGGBB`) | 422  | `validation_error`                       | `Certains champs sont invalides.` / `Some fields are invalid.`, plus the error of the field   |
| Missing or invalid access token                                   | 401  | `not_authenticated`                      | Handled by the API client: refresh of the session, otherwise back to `/login`                 |

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

| Method and path                          | Body                         | Success                      | Errors                     |
| ---------------------------------------- | ---------------------------- | ---------------------------- | -------------------------- |
| `POST /templates`                        | `{name}`                     | `201` `TemplateResponse`     | `401`, `422`               |
| `GET /templates`                         | —                            | `200` `TemplateListResponse` | `401`                      |
| `GET /templates/{id}`                    | —                            | `200` `TemplateResponse`     | `401`, `404`               |
| `PATCH /templates/{id}`                  | `{name}`                     | `200` `TemplateResponse`     | `401`, `404`, `422`        |
| `POST /templates/{id}/tiers`             | —                            | `201` `TemplateResponse`     | `401`, `404`               |
| `PATCH /templates/{id}/tiers/{tier_id}`  | `{name?, color?, position?}` | `200` `TemplateResponse`     | `401`, `404`, `422`        |
| `DELETE /templates/{id}/tiers/{tier_id}` | —                            | `200` `TemplateResponse`     | `401`, `404`, `409`        |
| `POST /templates/{id}/tiles`             | `{text}`                     | `201` `TemplateResponse`     | `401`, `404`, `409`, `422` |
| `PATCH /templates/{id}/tiles/{tile_id}`  | `{text?, position?}`         | `200` `TemplateResponse`     | `401`, `404`, `422`        |
| `DELETE /templates/{id}/tiles/{tile_id}` | —                            | `200` `TemplateResponse`     | `401`, `404`               |
| `DELETE /templates/{id}`                 | —                            | `204`                        | `401`, `404`               |

- `TemplateResponse` is `{id, name, created_at, updated_at, tiers: [{id, name, color, position}], tiles: [{id, text, position}], max_tiles}`, tiers and tiles sorted by `position`.
- `TemplateListResponse` is `{items: [{id, name, tile_count, updated_at}]}`. An object rather than an array, so that pagination (#105) can add a field without breaking the contract. The list is read in **one query**: the database counts the tiles (no N+1).
- The tier and tile routes return the whole template, so that the editor replaces its copy without reading it again. The `404` is `template_not_found` for the template, `tier_not_found` / `tile_not_found` for a tier or a tile that is not in it.

### 2.6 Known limitations

- No pagination of the list yet (#105).
- No super admin view of deleted templates yet (#104).
- Tiles have no image yet (#81, decided in the [images guide](images.md)): a tile is a text.

## 3. In the code

### Backend (`backend/app/`)

| Layer         | File                                                                          | Content                                                                                                                                                                                                                                                         |
| ------------- | ----------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Routes        | `api/routes/templates.py`                                                     | The `/templates` routes, the tier and tile routes; map the domain exceptions to `404` `template_not_found` / `tier_not_found` / `tile_not_found`, `409` `last_tier` / `tile_limit_reached` (param `max_tiles`).                                                 |
| Dependencies  | `api/dependencies.py`, `api/responses.py`                                     | `get_template_service`; `UNAUTHORIZED_RESPONSE`, the `401` documented in OpenAPI, shared with the `/auth` routes.                                                                                                                                               |
| Schemas       | `schemas/templates.py`                                                        | `CreateTemplateRequest`, `RenameTemplateRequest` (shared `TemplateName` rule), `UpdateTierRequest` (`TierName`, `TierColor`, `Position`), `CreateTileRequest`, `UpdateTileRequest` (`TileText`), `TemplateResponse` (with `max_tiles`), `TemplateListResponse`. |
| Service       | `services/templates.py`                                                       | `TemplateService`: create with the default tiers, list, get, rename, add / update / delete a tier or a tile (`_move`, `_renumber` shared by both, `_get_for_change` (locked), `_save_change`), soft delete, `purge_deleted`. Owns the transactions (`commit`).  |
| Repository    | `repositories/templates.py`                                                   | Queries only: active template of an owner (with tiers and tiles, locked with `for_update`), list with tile count, purge.                                                                                                                                        |
| Models        | `models/template.py`, `models/tier.py`, `models/tile.py`, `db/mixins.py`      | One file per class; the mixins of §2.2.                                                                                                                                                                                                                         |
| Exceptions    | `exceptions/templates.py`                                                     | `TemplateNotFoundError`, `TierNotFoundError`, `LastTierError`, `TileNotFoundError`, `TileLimitReachedError` (carries `max_tiles`).                                                                                                                              |
| Constants     | `constants/templates.py`, `constants/error_codes.py`, `constants/messages.py` | Lengths tied to the schema, `DEFAULT_TIERS`, `NEW_TIER_NAME` / `NEW_TIER_COLOR`, `FREE_PLAN_MAX_TILES`, the codes `TEMPLATE_NOT_FOUND`, `TIER_NOT_FOUND`, `LAST_TIER`, `TILE_NOT_FOUND`, `TILE_LIMIT_REACHED` and their developer messages.                     |
| Configuration | `core/config.py`                                                              | `DELETED_TEMPLATE_RETENTION_DAYS`.                                                                                                                                                                                                                              |
| Migration     | `migrations/versions/855df2a2ea2b_create_templates_tiers_and_tiles.py`        | Creates the three tables.                                                                                                                                                                                                                                       |
| Command       | `scripts/purge_deleted_templates.py` (in `backend/`)                          | Purge of §2.3.                                                                                                                                                                                                                                                  |

### Frontend (`frontend/src/`)

| Layer        | File                                                            | Content                                                                                                                                                                                                                                                                                                                                                                    |
| ------------ | --------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| API          | `api/templates.ts`                                              | One function per endpoint used and the hooks `useTemplates`, `useTemplate`, `useCreateTemplate`, `useDeleteTemplate`, `useRenameTemplate`, `useAddTier`, `useUpdateTier`, `useDeleteTier`, `useAddTile`, `useUpdateTile`, `useDeleteTile`. They all go through `useTemplateChange`, which stores the returned template and shows moves at once (optimistic), in one place. |
| Constants    | `constants/templates.ts`, `constants/routes.ts`                 | `TEMPLATE_NAME_MAX_LENGTH`, `TIER_NAME_MAX_LENGTH`, `TILE_TEXT_MAX_LENGTH` (equal to the backend), the query keys; `ROUTES.TEMPLATES`, `ROUTES.TEMPLATE_EDITOR` and `templateEditorPath(id)`. The tile limit is not a constant: it comes from `max_tiles`.                                                                                                                 |
| Pages        | `pages/TemplatesPage.tsx`                                       | _My templates_ (`/templates`): name, number of tiles and last modification date of each template, empty state, loading and error states.                                                                                                                                                                                                                                   |
|              | `pages/TemplateEditorPage.tsx`                                  | `/templates/:templateId`: the editor. Name of the template, its tiers and its tiles.                                                                                                                                                                                                                                                                                       |
| Components   | `components/CreateTemplateDialog.tsx`                           | Native `<dialog>`: required name, error of the field from the `422`, then opens the new template.                                                                                                                                                                                                                                                                          |
|              | `components/DeleteTemplateDialog.tsx`                           | Native `<dialog>` of confirmation; the list is refreshed after the deletion.                                                                                                                                                                                                                                                                                               |
|              | `components/TemplateNameField.tsx`, `components/TierEditor.tsx` | Name of the template; tiers: drag handle, color, name, move up / down, delete, add. Each change is saved at once.                                                                                                                                                                                                                                                          |
|              | `components/InlineEditField.tsx`, `components/ColorField.tsx`   | Field saved on Enter or when it loses focus (Escape restores the value); color picker in a popover (react-colorful: saturation and hue, suggested colors `TIER_COLOR_PRESETS`, hex code), saved once when it closes, Escape cancels.                                                                                                                                       |
|              | `components/SortableList.tsx`                                   | Drag and drop with [dnd-kit](https://dndkit.com/), mouse and keyboard, with translated announcements for screen readers.                                                                                                                                                                                                                                                   |
|              | `components/TileEditor.tsx`                                     | Tiles: counter `n / max_tiles`, grid of tiles (drag handle, text, move before / after, delete), form to add a tile, disabled once the limit is reached.                                                                                                                                                                                                                    |
| Navigation   | `components/MainNav.tsx` (in `Layout.tsx`)                      | Links _Home_ and _My templates_ in the header, shown once signed in.                                                                                                                                                                                                                                                                                                       |
| Translations | `i18n/locales/fr.ts`, `en.ts`                                   | `nav.*`, `templates.*` (number of tiles with plural forms, date in the language of the interface, `templates.editor.*` with the drag and drop announcements) and `errors.api.{template_not_found, tier_not_found, last_tier, tile_not_found, tile_limit_reached}`.                                                                                                         |

Creating or deleting a template invalidates the `['templates']` cache: the list and the opened templates are read again. A change in the editor puts the returned template in the cache and only reads the list again.

### Tests

`backend/tests/integration/test_templates.py` (endpoints) and `test_template_purge.py` (purge), against a real PostgreSQL; `frontend/src/pages/TemplatesPage.test.tsx` and `TemplateEditorPage.test.tsx` for the screens. All are described in the [testing guide](testing.md).
