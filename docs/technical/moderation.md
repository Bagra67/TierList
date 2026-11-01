# Moderation

English | [Français](moderation.fr.md)

How the moderation of public content is built: the **moderation log** (#267) and the first actions, on **images** (#124). The super admin role and how it is checked are in the [authentication guide](authentication.md#super-admins); what moderation does for the user: [user stories](../product/milestone-2/user-stories.md) (epic E1), [lifecycles](../product/milestone-2/lifecycles.md).

## 1. Functional overview

Every decision of a super admin (dismiss a report, hide, unhide or delete a content, ban or lift a ban) is written to the **moderation log** (US-1.9): **who** decided, **when**, **what** (the action and its target) and **why** (the reason).

- Only super admins see the log, in the moderation area (`/moderation/log`): newest first, 50 entries at a time ("Voir plus"), filtered by **target** (a text searched in the target's name) or by **super admin**.
- Nobody can edit or delete an entry: there is no route for it. Only the nightly purge deletes the entries older than **3 years** (the retention announced by the [privacy policy](legal-pages.md)).
- An entry stays readable after the target or the super admin's account is deleted: it keeps a copy of their names.

The first actions that write to the log are those on images (#124): hide, unhide or delete an image (§2.2). The other targets come with their issues (#268: hide or delete a template).

## 2. Technical design

### 2.1 The `moderation_actions` table

| Column         | Content                                                                                                                            |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `created_at`   | Time of the action (`clock_timestamp()`), indexed: the log is sorted on it. No `updated_at`: an entry never changes.               |
| `actor_id`     | The super admin (`users.id`), indexed for the filter. `ON DELETE SET NULL`: deleting the account keeps the entry.                  |
| `actor_name`   | Copy of the super admin's display name at the time of the action.                                                                  |
| `action`       | `ModerationActionKind`: `dismiss`, `hide`, `unhide`, `delete`, `ban`, `lift_ban`. Text with a CHECK constraint (`text_enum`).      |
| `target_type`  | `ModerationTargetType`: `template`, `image`, `account`, `nickname`, `game`.                                                        |
| `target_id`    | Id of the target, **without foreign key**: the target can be deleted, the entry stays. Empty when the target has no id of its own. |
| `target_label` | Copy of the target's name at the time of the action (template name, account name, nickname…), at most 200 characters.              |
| `reason`       | The reason written by the super admin, at most 500 characters.                                                                     |

Copying the names follows the closed games (`game_players.display_name`): the log must stay complete for the other super admins, whatever happens to the account or the content later.

### 2.2 Writing an entry

Every moderation action calls `ModerationLogService.record(actor, action, target_type, target_id, target_label, reason)` **inside its own transaction**. `record` adds the entry and flushes, but **does not commit**: the action commits, so that the action and its trace succeed or fail together (never a hidden template without its entry, nor an entry for an action that failed).

`ImageModerationService` (`app/services/image_moderation.py`) is the example to follow. It receives `ModerationLogService` by injection (`get_image_moderation_service`), with the same session as the request, and each action changes the status and records the entry before one commit:

```python
image.status = ImageStatus.HIDDEN
self._moderation_log.record(
    super_admin,
    ModerationActionKind.HIDE,
    ModerationTargetType.IMAGE,
    image.id,
    image.storage_key,  # no file name is stored: the key is unique
    reason,
)
self._session.commit()
```

Actions that exist:

| Method | Path                                   | Action and target | Allowed from        |
| ------ | -------------------------------------- | ----------------- | ------------------- |
| `POST` | `/moderation/images/{image_id}/hide`   | `hide`, `image`   | `visible`           |
| `POST` | `/moderation/images/{image_id}/unhide` | `unhide`, `image` | `hidden`            |
| `POST` | `/moderation/images/{image_id}/delete` | `delete`, `image` | `visible`, `hidden` |

- Body `{reason}` (`ModerationReasonRequest`: the reason, 1 to 500 characters, surrounding spaces removed); answer `204`; `404` `image_not_found`, `409` `image_moderation_conflict` when the action does not apply to the current status. Protected like the log (§2.3).
- `POST` rather than `DELETE`: the action carries a reason in its body, and the row of the image stays.
- The image is locked (`SELECT … FOR UPDATE`) during the action; its file moves to or from a private quarantine, or is erased, in an order that fails on the safe side. Details: [images guide](images.md#29-moderation).
- No page calls these routes yet: the super admin pages that list images (#125, #126, #127) will. Until then, they can be tried from Swagger (`/docs`).

A new action or target type is a new enum value: `text_enum` stores text with a CHECK constraint, so the migration only updates the constraint (no `ALTER TYPE`).

### 2.3 Reading the log

| Method | Path                       | Answer                                                                     |
| ------ | -------------------------- | -------------------------------------------------------------------------- |
| `GET`  | `/moderation/log`          | `{ entries, has_more }`: one page of the log, newest first.                |
| `GET`  | `/moderation/super-admins` | `[{ id, display_name }]` by name: the options of the "Super admin" filter. |

- Both are protected by `SuperAdminDep` and declare `SUPER_ADMIN_RESPONSES` (`401` without a session, `403` `super_admin_required` for another account).
- `/moderation/log` takes `limit` (50 by default, 100 at most), `offset`, `actor_id` and `target`. Pagination works like the [history](results.md#28-history): the service reads `limit + 1` entries to know whether another page exists, and the order `created_at desc, id` never skips an entry between two pages.
- `target` is searched in `target_label`, case-insensitive (`ILIKE`), with `%` and `_` read as plain characters (`icontains(..., autoescape=True)`).

### 2.4 Purge

`ModerationLogService.purge_expired` deletes the entries older than `MODERATION_LOG_RETENTION_DAYS` (1095 days by default) and commits. It runs every night with the other purges (`purge_moderation_log` in `maintenance.py`, [deployment guide](deployment.md#23-nightly-tasks)); it is the only place where an entry is deleted. There is no command-line script: the nightly task is enough.

### 2.5 The page

`/moderation` leads to `/moderation/log` as long as the log is the only page of the moderation area. `ModerationLayout` shows the side menu of the area (only "Journal" for now; the reports and the recent uploads come with their issues) inside `RequireSuperAdmin`.

`ModerationLogPage` shows a table (when, who, action, target, reason) that scrolls on its own on a small screen. The **Cible** filter is applied when the search is sent (button or Enter): one request per search, not one per key; the **Super admin** filter is applied at once. The filters are part of the query key of `useModerationLog`, so changing them starts again from the first page.

### 2.6 Settings

| Variable                        | Meaning                                     | Default |
| ------------------------------- | ------------------------------------------- | ------- |
| `MODERATION_LOG_RETENTION_DAYS` | Days an entry of the moderation log is kept | `1095`  |

Changing it means changing the privacy policy too ([legal pages](legal-pages.md)).

## 3. In the code

| Layer        | File                                                                                  | Content                                                                                                                 |
| ------------ | ------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Routes       | `backend/app/api/routes/moderation.py`                                                | `GET /moderation/log`, `GET /moderation/super-admins`, `POST /moderation/images/{image_id}/hide`, `/unhide`, `/delete`. |
| Schemas      | `backend/app/schemas/moderation.py`                                                   | `ModerationActionResponse`, `ModerationLogResponse`, `SuperAdminResponse`, `ModerationReasonRequest`.                   |
| Service      | `backend/app/services/moderation_log.py`                                              | `ModerationLogService`: `record`, `page`, `super_admins`, `purge_expired`.                                              |
| Service      | `backend/app/services/image_moderation.py`                                            | `ImageModerationService`: `hide`, `unhide`, `delete` ([images guide](images.md)).                                       |
| Repositories | `repositories/moderation_actions.py`, `repositories/users.py`                         | Queries: add, list with filters, delete before a date; the super admins by name.                                        |
| Model        | `backend/app/models/moderation_action.py`                                             | `ModerationAction` (`moderation_actions`); enums in `models/enums.py`.                                                  |
| Constants    | `backend/app/constants/moderation.py`                                                 | Lengths of the reason and the label, page sizes.                                                                        |
| Migration    | `migrations/versions/1c5aea95404b_create_moderation_actions.py`                       | Creates the table, its CHECK constraints and indexes.                                                                   |
| Frontend     | `api/moderation.ts`, `components/ModerationLayout.tsx`, `pages/ModerationLogPage.tsx` | Hooks, area menu, log page.                                                                                             |

Tests: [testing guide](testing.md) (`test_moderation_log.py`, `test_moderation_routes.py`, `test_image_moderation.py`, `ModerationLogPage.test.tsx`).
