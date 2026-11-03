# Moderation

English | [Français](moderation.fr.md)

How the moderation of public content is built: the **moderation log** (#267), the actions on **images** (#124) and on **templates** (#268), the **recent uploads** page that calls the image ones (#125), and the **accounts**: their search, their page and their **bans** (#127). The super admin role and how it is checked are in the [authentication guide](authentication.md#super-admins); what moderation does for the user: [user stories](../product/milestone-2/user-stories.md) (epic E1), [lifecycles](../product/milestone-2/lifecycles.md).

## 1. Functional overview

Every decision of a super admin (dismiss a report, hide, unhide or delete a content, ban or lift a ban) is written to the **moderation log** (US-1.9): **who** decided, **when**, **what** (the action and its target) and **why** (the reason).

- Only super admins see the log, in the moderation area (`/moderation/log`): newest first, 50 entries at a time ("Voir plus"), filtered by **target** (a text searched in the target's name) or by **super admin**.
- Nobody can edit or delete an entry: there is no route for it. Only the nightly purge deletes the entries older than **3 years** (the retention announced by the [privacy policy](legal-pages.md)).
- An entry stays readable after the target or the super admin's account is deleted: it keeps a copy of their names.

The actions that write to the log are those on images (#124) and on templates (#268): hide, unhide or delete an image or a template (§2.2), and those on accounts (#127): ban or lift a ban (§2.9). The other targets come with their issues. A template hidden by the moderation no longer opens a room nor starts a game, while its owner still edits it and sees the reason ([templates guide](templates.md#27-moderation)). The template actions are called from the account page (§2.8); the reports queue (#269) will call them too.

Super admins also review the **recent uploads** (US-1.7, #125), the first page of the moderation area (`/moderation/uploads`): the latest images, newest first, with their author, date and use (templates, games), filtered by author, upload days and status (§2.6). Each image can be hidden, unhidden or deleted from there, with a reason. A hidden image stays visible to super admins only, through a temporary link. The [privacy policy](legal-pages.md) says that super admins see the uploaded images with their author's name.

Super admins also find an **account** (US-1.8, #127), for instance after a report received by email: the **Comptes** page (`/moderation/accounts`) searches by name or email, and the **page of an account** (`/moderation/accounts/{id}`) gathers its details, its templates and its images with their actions, a "hide all their images" button, its **ban** and the history of the decisions about it (§2.8). An account can be **banned** temporarily, until a day included, or **permanently**, with a reason shown to the person when they try to sign in (§2.9): it is signed out everywhere and can no longer sign in until the ban ends or is lifted. A super admin can never be banned. The [privacy policy](legal-pages.md) describes the ban data, kept until the account is deleted, says that a banned person sees the reason at sign-in, and what the super admins see of an account.

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

`ImageModerationService` (`app/services/image_moderation.py`) is the example to follow; `TemplateModerationService` (`app/services/template_moderation.py`, injected by `get_template_moderation_service`) works the same way. It receives `ModerationLogService` by injection (`get_image_moderation_service`), with the same session as the request, and each action changes the status and records the entry before one commit:

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

| Method | Path                                         | Action and target    | Allowed from                               |
| ------ | -------------------------------------------- | -------------------- | ------------------------------------------ |
| `POST` | `/moderation/images/{image_id}/hide`         | `hide`, `image`      | `visible`                                  |
| `POST` | `/moderation/images/{image_id}/unhide`       | `unhide`, `image`    | `hidden`                                   |
| `POST` | `/moderation/images/{image_id}/delete`       | `delete`, `image`    | `visible`, `hidden`                        |
| `POST` | `/moderation/templates/{template_id}/hide`   | `hide`, `template`   | visible (`moderation` `none`), not deleted |
| `POST` | `/moderation/templates/{template_id}/unhide` | `unhide`, `template` | `moderation` `hidden`, not deleted         |
| `POST` | `/moderation/templates/{template_id}/delete` | `delete`, `template` | visible or hidden, not deleted             |

- Body `{reason}` (`ModerationReasonRequest`: the reason, 1 to 500 characters, surrounding spaces removed); answer `204`; `404` `image_not_found` / `template_not_found` (a purged template is not found), `409` `image_moderation_conflict` / `template_moderation_conflict` when the action does not apply to the current status. Protected like the log (§2.3).
- `POST` rather than `DELETE`: the action carries a reason in its body, and the row of the image or the template stays.
- The image is locked (`SELECT … FOR UPDATE`) during the action; its file moves to or from a private quarantine, or is erased, in an order that fails on the safe side. Details: [images guide](images.md#29-moderation).
- The template is locked the same way, whatever its owner, deleted or not (`get_template_for_update`). Hiding stores `moderation` `hidden` and copies the reason on the template, since the log is purged after 3 years; unhiding clears it; deleting sets `deleted_at` like a deletion by the owner (then the nightly purge). The change goes through an `UPDATE` that keeps `updated_at`, the owner's last change. The log entry targets `template`, with the template name as label. Details: [templates guide](templates.md#27-moderation).
- The recent uploads page (§2.6) and the account page (§2.8) call the image actions; the account page also calls the template ones; the reports queue (#269) will call both. The account actions (ban, lift a ban, hide all the images) are in §2.8 and §2.9.

A new action or target type is a new enum value: `text_enum` stores text with a CHECK constraint, so the migration only updates the constraint (no `ALTER TYPE`).

### 2.3 Reading the log

| Method | Path                       | Answer                                                                     |
| ------ | -------------------------- | -------------------------------------------------------------------------- |
| `GET`  | `/moderation/log`          | `{ entries, has_more }`: one page of the log, newest first.                |
| `GET`  | `/moderation/super-admins` | `[{ id, display_name }]` by name: the options of the "Super admin" filter. |

- Both are protected by `SuperAdminDep` and declare `SUPER_ADMIN_RESPONSES` (`401` without a session, `403` `super_admin_required` for another account).
- `/moderation/log` takes `limit` (50 by default, 100 at most), `offset`, `actor_id`, `target` and `account_id`. Pagination works like the [history](results.md#28-history): the service reads `limit + 1` entries to know whether another page exists, and the order `created_at desc, id` never skips an entry between two pages.
- `target` is searched in `target_label`, case-insensitive (`ILIKE`), with `%` and `_` read as plain characters (`icontains(..., autoescape=True)`).
- `account_id` keeps the decisions about an account (the history of its page, §2.8): the entries whose target is the account itself, one of its templates or one of its images (`target_id` compared to the account id and to the ids of its templates and images, in sub-queries). An entry about a template purged since then no longer matches: its row is gone.

### 2.4 Purge

`ModerationLogService.purge_expired` deletes the entries older than `MODERATION_LOG_RETENTION_DAYS` (1095 days by default) and commits. It runs every night with the other purges (`purge_moderation_log` in `maintenance.py`, [deployment guide](deployment.md#23-nightly-tasks)); it is the only place where an entry is deleted. There is no command-line script: the nightly task is enough.

### 2.5 The page

`/moderation` leads to the first page of the menu, the recent uploads (`/moderation/uploads`, §2.6). `ModerationLayout` shows the side menu of the area, "Derniers envois", "Comptes" then "Journal" (the reports come with their issue), inside `RequireSuperAdmin`.

`ModerationLogPage` shows a table (when, who, action, target, reason) that scrolls on its own on a small screen. The **Cible** filter is applied when the search is sent (button or Enter): one request per search, not one per key; the **Super admin** filter is applied at once. The filters are part of the query key of `useModerationLog`, so changing them starts again from the first page.

The table and its "Voir plus" are the shared `ModerationLogTable` component, which takes the filters and the empty message: the log page and the history of an account page (§2.8) both use it. A target of type `account` is a link to the page of that account (an account deleted since then shows the not found error there).

### 2.6 Recent uploads

The first page of the moderation area (US-1.7, #125): the latest uploaded images, to spot a problem before anyone reports it, and act on it at once.

| Method | Path                 | Answer                                                                           |
| ------ | -------------------- | -------------------------------------------------------------------------------- |
| `GET`  | `/moderation/images` | `{ images, has_more }`: one page of the visible and hidden images, newest first. |

- Protected by `SuperAdminDep` and declares `SUPER_ADMIN_RESPONSES`, like the log (§2.3).
- Parameters:
  - `limit` (24 by default, a grid of 3 columns; 96 at most) and `offset`;
  - `author`: a text searched in the display name **or** the email of the author, case-insensitive, with `%` and `_` read as plain characters (`icontains(..., autoescape=True)`); at most the maximum length of an email;
  - `created_after` (included) and `created_before` (excluded): the upload period, as `AwareDatetime`. The time zone is required: a date without it is refused with `422`, since it would be ambiguous;
  - `status`: `visible` or `hidden`; without it, both. A `deleted` image has no file left and is **never listed**;
  - `owner_id`: the images of one author only, those of the account page (§2.8).
- Each image: `{ id, url, status, created_at, author_id, author_name, template_names, game_count }`. `author_id` leads to the account page of the author; `author_id` and `author_name` are `null` once the author deleted their account; `template_names` are the templates, not deleted, whose tiles show the image, in alphabetical order; `game_count` is the number of distinct games, ongoing or closed, played on a snapshot that shows it.
- Order `created_at desc, id` (the id breaks the ties) and `limit + 1` images read to fill `has_more`, like the log. The `ix_images_created_at` index (migration `4840e3c37d23`) serves the sort.
- A page costs **3 queries**, whatever its size (no N+1), put together by `RecentUploadsService` (`app/services/recent_uploads.py`): the images with their author's name (`list_recent_images`, outer join on `users`), then the template names of all the images of the page (`template_names_by_image`, tiles joined to the templates without `deleted_at`), then their number of games (`game_counts_by_image`, `snapshot_tiles` joined to `games` on `snapshot_id`, distinct games counted).
- **Address of a hidden image**: its file is no longer at its public address. `recent_upload_response` (`app/api/presenters/images.py`) gives a **presigned URL** of its quarantine file instead (`ImageStorage.presigned_url`, valid for 15 minutes). The backend serves no bytes and the quarantine stays private; whoever holds the link can read the file for 15 minutes. Details: [images guide](images.md#29-moderation).

The page, `RecentUploadsPage` (`/moderation/uploads`):

- **Filters**: **Auteur** is applied when the search is sent (button or Enter), like **Cible** in the log. **Du** and **Au** are days, in the super admin's time zone, sent as the start of the first day and the start of the day after the last one (ISO dates with time zone): the last day is included. **Statut**: all, visible or hidden. The filters are part of the query key of `useRecentUploads` (`useInfiniteQuery`), so changing them starts again from the first page; "Voir plus" reads the next page, from the number of images already shown.
- **Cards** (`UploadCard`): the image (its alternative text gives the author and the date); a **Masquée** badge written in text on a hidden image, not only a color; the author, or "Compte supprimé"; the date; the number of templates and of games (i18next plurals); the template names (i18next `list` formatter). The author is a link to the page of their account (§2.8); the template names are plain text until a template page exists.
- **Actions**, according to the status: **Masquer** and **Supprimer** on a visible image, **Réafficher** and **Supprimer** on a hidden one. Their accessible names give the author and the date of the image.
- Each action opens **`ModerationReasonDialog`**, a generic dialog (title, description, button labels, destructive or not) also used by the account page (§2.8) and meant for the reports queue (#269). The reason is required and cannot be only spaces, at most 500 characters (`MODERATION_REASON_MAX_LENGTH`, mirrored in `frontend/src/constants/moderation.ts`; the backend stays the authority). The button is red for a deletion and disabled while the action runs (no double submission); a failure shows its translated error in the dialog, which closes once the action succeeded.
- `useModerateImage` calls the action route (§2.2), then invalidates the recent uploads and the log, which are read again.
- The grid, its "Voir plus" and the image actions are the shared `UploadGrid` component, which takes the filters and the empty message: the recent uploads page and the account page (§2.8, filtered on `ownerId`) both use it. The day filters are turned into dates by `components/localDays.ts`, shared with the ban dialog (§2.9).

### 2.7 Settings

| Variable                        | Meaning                                     | Default |
| ------------------------------- | ------------------------------------------- | ------- |
| `MODERATION_LOG_RETENTION_DAYS` | Days an entry of the moderation log is kept | `1095`  |

Changing it means changing the privacy policy too ([legal pages](legal-pages.md)).

### 2.8 Accounts

Finding an account and acting on it as a whole (US-1.8, #127), for instance after a report received by email.

| Method | Path                                         | Answer                                                                                 |
| ------ | -------------------------------------------- | -------------------------------------------------------------------------------------- |
| `GET`  | `/moderation/accounts`                       | `{ accounts, has_more }`: one page of the accounts, by name.                           |
| `GET`  | `/moderation/accounts/{user_id}`             | The account page: its details, its active ban and its templates.                       |
| `POST` | `/moderation/accounts/{user_id}/hide-images` | `{ hidden_count }`: hides each visible image of the account. Body `{reason}`.          |
| `POST` | `/moderation/accounts/{user_id}/ban`         | `204`: bans the account (§2.9). Body `{reason, ends_at}`.                              |
| `POST` | `/moderation/accounts/{user_id}/lift-ban`    | `204`: lifts the active ban (§2.9). Body `{reason}` (`ModerationReasonRequest`, §2.2). |

- All protected by `SuperAdminDep` and declaring `SUPER_ADMIN_RESPONSES`, like the log (§2.3). An unknown account gets `404` `account_not_found` (`UserNotFoundError` mapped by the route).
- **Search** (`AccountReviewService.search`, `search_users`): `query` is searched in the display name **or** the email, case-insensitive, with `%` and `_` read as plain characters (`icontains(..., autoescape=True)`), at most the maximum length of an email; without it, every account. Sorted by name, the id breaking the ties so that a page skips nothing; `limit` 50 by default, 100 at most (`ACCOUNT_SEARCH_PAGE_SIZE_*`), `offset`, and `limit + 1` accounts read to fill `has_more`, like the log. Each account: `{ id, display_name, email, created_at, role, banned }`; `banned` is computed for the whole page in **one query** (`AccountBanService.banned_user_ids`), not one per account.
- **Account page** (`AccountReviewService.details`): `{ id, display_name, email, created_at, email_verified, role, ban, templates }`. `ban` is the active ban (`{ created_at, ends_at, reason, actor_name }`) or `null`; `templates` are the active templates of the account (not deleted, most recently changed first, `TemplateService.list_for_owner`), with their moderation state. Its images are read through the recent uploads filtered on it (`owner_id`, §2.6), its history through the log filtered on it (`account_id`, §2.3): no route of its own.
- **Hide all their images** (`AccountReviewService.hide_all_images`): the visible images of the account, oldest first (`list_visible_image_ids_of_owner`, served by `ix_images_owner_id_created_at`), are each hidden through `ImageModerationService.hide`, exactly as one by one (US-1.4): the file goes to the quarantine and each image gets its own log entry. Each image is **committed on its own**: after a failure, the images already hidden stay hidden, and running it again resumes with those still visible. An image hidden or deleted meanwhile by another super admin is skipped (`ImageModerationConflictError`). The route is a `def`, not an `async def`: each image calls the S3 storage, which blocks.

The pages:

- **`ModerationAccountsPage`** (`/moderation/accounts`, "Comptes" in the menu): a **Nom ou e-mail** field applied when the search is sent (button or Enter), like **Cible** in the log; the list (name as a link to the account page, email, creation date, **Super admin** and **Banni** badges written in text); "Voir plus" (`useAccountSearch`, `useInfiniteQuery`).
- **`ModerationAccountPage`** (`/moderation/accounts/:accountId`, `useAccount`), in sections:
  - **details**: name, **Super admin** badge, email, creation date, confirmed email or not;
  - **ban** (§2.9): the active ban (permanent or until a date, reason, by whom and when) with **Lever le bannissement** and **Modifier le bannissement**, or **Bannir ce compte**; for a super admin, only a sentence saying they cannot be banned, no button;
  - **templates**: each with its number of tiles, the **Masqué** badge, and **Masquer** or **Réafficher**, and **Supprimer**, each through `ModerationReasonDialog` (`useModerateTemplate`, which reads the account page and the log again);
  - **images**: `UploadGrid` filtered on the account (§2.6), with **Masquer toutes ses images** (`useHideAllImages`, a `ModerationReasonDialog`, then a status message with the number of images hidden);
  - **history**: `ModerationLogTable` filtered on the account (§2.5).
- Links lead to the account page from the author of an image (`UploadCard`) and from an `account` target of the log (`ModerationLogTable`). `moderationAccountPath` (`constants/routes.ts`) builds the path.
- A reports section (the reports about the account and those it sent) comes with the reports (#126, #269).

### 2.9 Account bans

An account can be banned temporarily or permanently (US-1.8). Not to be confused with `RoomBan`, the ban from one room by its host.

**The `account_bans` table** (`AccountBan`, migration `39be2b56f131`):

| Column       | Content                                                                                                                         |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| `user_id`    | The banned account, indexed. `ON DELETE CASCADE`: the bans are **kept until the account is deleted**, to spot a repeat offence. |
| `actor_id`   | The super admin who decided it. `ON DELETE SET NULL`.                                                                           |
| `actor_name` | Copy of the super admin's display name, readable after their account is deleted (like the log, §2.1).                           |
| `reason`     | The reason, at most 500 characters, **shown to the person** when they try to sign in.                                           |
| `ends_at`    | End of a temporary ban; `null` for a permanent ban.                                                                             |
| `lifted_at`  | When a super admin lifted it, or when a new ban replaced it.                                                                    |
| `created_at` | When it was decided (plus `updated_at`, like every table).                                                                      |

**Rules** (`AccountBanService`, `app/services/account_bans.py`):

- A ban is **active** when it is not lifted and has no end or an end in the future (`is_active` in `repositories/account_bans.py`). A temporary ban therefore **ends by itself**, without a scheduled task: nothing is written when it ends.
- At most **one active ban** per account: banning an account already banned first lifts the current ban (`lifted_at`), then adds the new one: from temporary to permanent, or another end. The account row is locked (`SELECT … FOR UPDATE`, `get_user_for_update`) during a ban or a lift, so two simultaneous bans never leave two active bans.
- A super admin can **never** be banned, neither by another one nor by themselves: `409` `cannot_ban_super_admin`.
- `ends_at` is an `AwareDatetime` (time zone required, otherwise `422`); an end that is not in the future gets `422` `ban_end_in_past`.
- Lifting needs an active ban: `409` `account_not_banned` otherwise.
- Each ban and each lift is written to the log (`ban` / `lift_ban`, target `account`, the display name as label) in the same transaction (§2.2).

**Effects of a ban**, in the same transaction:

- **Signed out everywhere**, like after a password reset: the refresh tokens of the account are revoked (no session can be refreshed) and `users.token_version` is incremented, so every access token already issued is refused at the next request ([authentication guide](authentication.md#banned-accounts)).
- **Sign-in refused** while the ban is active, with a password or with Google, with the reason and the end ([authentication guide](authentication.md#banned-accounts)). Refreshing is refused too, for a session that a sign-in in progress would have opened during the ban.
- Lifting a ban only lets the account sign in again; its sessions stay closed.

The frontend:

- **`BanAccountDialog`**: **Temporairement** (a day field, from today, "Jusqu'au (inclus)") or **Définitivement**, and the **reason**, with a label saying the person will see it. The chosen day is included: `ends_at` is the start of the next day in the super admin's time zone (`startOfNextDay`, `components/localDays.ts`). The button is red and disabled until the form is complete and while the request runs; an error shows its translated message in the dialog. The same dialog changes an active ban.
- **Lifting** goes through `ModerationReasonDialog`. `useBanAccount` and `useLiftBan` then read the account page, the search (its **Banni** badge) and the log again.
- `translateError` (`errors/apiError.ts`) turns every error param whose name ends in `_at` into a `Date`, so that the i18next `datetime` formatter shows the `ends_at` of `account_banned_until` in the interface language.

**Known limitations**:

- The realtime sockets already open are not closed at once: they only signal that the room must be read again, and every REST call of the banned account fails from then on.
- The public templates of a banned account are not hidden from a marketplace yet: there is no marketplace (#277).

## 3. In the code

| Layer        | File                                                                                                                                                                                                                                                                                                                                                                                                                                               | Content                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Routes       | `backend/app/api/routes/moderation.py`                                                                                                                                                                                                                                                                                                                                                                                                             | `GET /moderation/log`, `GET /moderation/super-admins`, `GET /moderation/images`, `POST /moderation/images/{image_id}/hide`, `/unhide`, `/delete`, `POST /moderation/templates/{template_id}/hide`, `/unhide`, `/delete`, `GET /moderation/accounts`, `GET /moderation/accounts/{user_id}`, `POST /moderation/accounts/{user_id}/hide-images`, `/ban`, `/lift-ban`.                                                                       |
| Schemas      | `backend/app/schemas/moderation.py`                                                                                                                                                                                                                                                                                                                                                                                                                | `ModerationActionResponse`, `ModerationLogResponse`, `SuperAdminResponse`, `ModerationReasonRequest`, `RecentUploadResponse`, `RecentUploadsResponse`, `AccountSummaryResponse`, `AccountSearchResponse`, `AccountResponse`, `AccountBanResponse`, `HiddenImagesResponse`, `BanAccountRequest`.                                                                                                                                          |
| Presenter    | `backend/app/api/presenters/images.py`                                                                                                                                                                                                                                                                                                                                                                                                             | `recent_upload_response`: public URL, or presigned quarantine URL for a hidden image.                                                                                                                                                                                                                                                                                                                                                    |
| Service      | `backend/app/services/moderation_log.py`                                                                                                                                                                                                                                                                                                                                                                                                           | `ModerationLogService`: `record`, `page`, `super_admins`, `purge_expired`.                                                                                                                                                                                                                                                                                                                                                               |
| Service      | `backend/app/services/image_moderation.py`                                                                                                                                                                                                                                                                                                                                                                                                         | `ImageModerationService`: `hide`, `unhide`, `delete` ([images guide](images.md)).                                                                                                                                                                                                                                                                                                                                                        |
| Service      | `backend/app/services/template_moderation.py`                                                                                                                                                                                                                                                                                                                                                                                                      | `TemplateModerationService`: `hide`, `unhide`, `delete` ([templates guide](templates.md#27-moderation)).                                                                                                                                                                                                                                                                                                                                 |
| Service      | `backend/app/services/recent_uploads.py`                                                                                                                                                                                                                                                                                                                                                                                                           | `RecentUploadsService.page`: a page of recent uploads with their use.                                                                                                                                                                                                                                                                                                                                                                    |
| Service      | `backend/app/services/account_review.py`                                                                                                                                                                                                                                                                                                                                                                                                           | `AccountReviewService`: `search`, `details`, `hide_all_images` (§2.8).                                                                                                                                                                                                                                                                                                                                                                   |
| Service      | `backend/app/services/account_bans.py`                                                                                                                                                                                                                                                                                                                                                                                                             | `AccountBanService`: `ban`, `lift`, `active_ban`, `banned_user_ids` (§2.9).                                                                                                                                                                                                                                                                                                                                                              |
| Repositories | `repositories/moderation_actions.py`, `repositories/users.py`, `repositories/images.py`, `repositories/templates.py`, `repositories/account_bans.py`                                                                                                                                                                                                                                                                                               | Queries: add, list with filters, delete before a date; the super admins by name; the recent images, their templates and games; a template of any owner, locked (`get_template_for_update`); the accounts searched by name or email (`search_users`), an account locked (`get_user_for_update`), the visible images of an account (`list_visible_image_ids_of_owner`); the active ban (`is_active`, `get_active_ban`, `banned_user_ids`). |
| Model        | `backend/app/models/moderation_action.py`                                                                                                                                                                                                                                                                                                                                                                                                          | `ModerationAction` (`moderation_actions`); enums in `models/enums.py`.                                                                                                                                                                                                                                                                                                                                                                   |
| Model        | `backend/app/models/account_ban.py`                                                                                                                                                                                                                                                                                                                                                                                                                | `AccountBan` (`account_bans`, §2.9).                                                                                                                                                                                                                                                                                                                                                                                                     |
| Exceptions   | `backend/app/exceptions/moderation.py`, `exceptions/auth.py`                                                                                                                                                                                                                                                                                                                                                                                       | `CannotBanSuperAdminError`, `BanEndInPastError`, `AccountNotBannedError`; `UserNotFoundError`, `AccountBannedError` (sign-in).                                                                                                                                                                                                                                                                                                           |
| Constants    | `backend/app/constants/moderation.py`, `constants/images.py`                                                                                                                                                                                                                                                                                                                                                                                       | Lengths of the reason, the label, the author filter and the account search, page sizes (log, recent uploads, accounts); `IMAGE_PREVIEW_URL_EXPIRES_SECONDS` (900).                                                                                                                                                                                                                                                                       |
| Migration    | `migrations/versions/1c5aea95404b_create_moderation_actions.py`                                                                                                                                                                                                                                                                                                                                                                                    | Creates the table, its CHECK constraints and indexes.                                                                                                                                                                                                                                                                                                                                                                                    |
| Migration    | `migrations/versions/4840e3c37d23_add_created_at_index_to_images.py`                                                                                                                                                                                                                                                                                                                                                                               | `ix_images_created_at`, the sort of the recent uploads.                                                                                                                                                                                                                                                                                                                                                                                  |
| Migration    | `migrations/versions/507b5cf96d8d_add_moderation_to_templates.py`                                                                                                                                                                                                                                                                                                                                                                                  | `templates.moderation` and `templates.moderation_reason` ([templates guide](templates.md#27-moderation)).                                                                                                                                                                                                                                                                                                                                |
| Migration    | `migrations/versions/39be2b56f131_create_account_bans.py`                                                                                                                                                                                                                                                                                                                                                                                          | Creates `account_bans`, its foreign keys and the `user_id` index (§2.9).                                                                                                                                                                                                                                                                                                                                                                 |
| Frontend     | `api/moderation.ts`, `components/ModerationLayout.tsx`, `pages/ModerationLogPage.tsx`, `pages/RecentUploadsPage.tsx`, `components/UploadCard.tsx`, `components/ModerationReasonDialog.tsx`, `constants/moderation.ts`, `pages/ModerationAccountsPage.tsx`, `pages/ModerationAccountPage.tsx`, `components/BanAccountDialog.tsx`, `components/UploadGrid.tsx`, `components/ModerationLogTable.tsx`, `components/localDays.ts`, `errors/apiError.ts` | Hooks (`useModerationLog`, `useRecentUploads`, `useModerateImage`, `useAccountSearch`, `useAccount`, `useModerateTemplate`, `useHideAllImages`, `useBanAccount`, `useLiftBan`), area menu, log page, recent uploads page and its cards, reason dialog, reason length; accounts page, account page, ban dialog, shared image grid and log table, days to dates, `*_at` params turned into dates.                                          |

Tests: [testing guide](testing.md) (`test_moderation_log.py`, `test_moderation_routes.py`, `test_image_moderation.py`, `test_template_moderation.py`, `test_recent_uploads.py`, `ModerationLogPage.test.tsx`, `RecentUploadsPage.test.tsx`, `ModerationReasonDialog.test.tsx`, `test_account_review.py`, `test_account_bans.py`, `test_google_auth.py`, `ModerationAccountsPage.test.tsx`, `ModerationAccountPage.test.tsx`, `BanAccountDialog.test.tsx`, `LoginPage.test.tsx`, `apiError.test.ts`).
