# Rooms

English | [Français](rooms.fr.md)

How rooms are created, read and configured through the API: data model, code and link, settings, endpoints, the lobby, and where it lives in the code. **Built in #83** (API) and **#84** (screens, §3). What a room is for the user: [user stories](../product/milestone-1/user-stories.md) US-2.1 and US-2.2, [lifecycles](../product/milestone-1/lifecycles.md).

## 1. Functional overview

A room is where a group plays, reached by its **code** or its **link**. It is created from one of the user's templates, who becomes its **room admin**. Its **settings** apply to the next game.

| Action              | Endpoint                       | Result                                                                                                     |
| ------------------- | ------------------------------ | ---------------------------------------------------------------------------------------------------------- |
| Create a room       | `POST /rooms`                  | An open room on one of my templates with at least one tile; I am its room admin and its first participant. |
| Open a room         | `GET /rooms/{code}`            | The room, its settings and its participants, for a participant.                                            |
| Change the settings | `PATCH /rooms/{code}/settings` | The new settings (room admin only); during a game, only late arrivals.                                     |

### Rules

- **Template**: one of mine, not deleted, with **at least one tile** (US-2.1). Otherwise `404` `template_not_found` or `409` `template_has_no_tiles`. Several rooms can use the same template.
- **Code**: 6 characters among `ABCDEFGHJKLMNPQRSTUVWXYZ23456789` (no `0`, `O`, `1`, `I`, easily confused when read or dictated), random (`secrets`), unique. It is read case-insensitively: `k7p2qx` opens `K7P2QX`.
- **Link**: `FRONTEND_BASE_URL` + `/r/` + the code, e.g. `http://localhost:5173/r/K7P2QX`. The page itself comes with #84.
- **Room admin**: the creator. They get a **participant** row at once: they count in the participant limit even when they do not play (US-2.6).
- **Visibility**: a room is only visible to its **participants**. Anyone else gets `404` `room_not_found`, exactly like an unknown code: the API never reveals that a room exists. Joining a room comes with #86.
- **Settings** (US-2.2), with their default values:

  | Setting                 | Values                             | Default                         |
  | ----------------------- | ---------------------------------- | ------------------------------- |
  | `item_order`            | `template`, `random`               | `template`                      |
  | `auto_advance`          | `none`, `timer`, `everyone_placed` | `none` (manual only)            |
  | `timer_seconds`         | 5 to 300 s                         | `ROOM_DEFAULT_TIMER_SECONDS`    |
  | `cooldown_seconds`      | 10 to 600 s                        | `ROOM_DEFAULT_COOLDOWN_SECONDS` |
  | `admin_plays`           | `true`, `false`                    | `true`                          |
  | `late_arrivals_allowed` | `true`, `false`                    | `true`                          |

  `timer_seconds` is kept even when `auto_advance` is not `timer`: the chosen duration comes back if the timer is set again.

- **Only the room admin** changes the settings (`403` `room_admin_required` for another participant; [permissions](../product/permissions.md)).
- **During a game** (status `playing`), the settings are locked, **except late arrivals** (US-2.10): any other field answers `409` `room_settings_locked`.
- **Empty update**: a `PATCH` without any field (or with only `null` values) changes nothing.
- **Deletions**: purging a deleted template keeps the room, without template (`template: null`); no new game can then start in it. Deleting the room admin's account deletes their rooms and their participants.

### Messages

The API returns an error **code**; the frontend translates it (`errors.api.*` and `errors.field.*` in `frontend/src/i18n/locales/`).

| Situation                                              | HTTP | API code                                                                                | Translation (FR / EN)                                                                                                   |
| ------------------------------------------------------ | ---- | --------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Template unknown, deleted or of another user           | 404  | `template_not_found`                                                                    | `Ce template est introuvable.` / `This template could not be found.`                                                    |
| Template without tiles                                 | 409  | `template_has_no_tiles`                                                                 | `Ajoutez au moins une tuile à ce template pour jouer avec.` / `Add at least one tile to this template to play with it.` |
| Room unknown, or the user has no seat in it            | 404  | `room_not_found`                                                                        | `Cette salle est introuvable ou a été fermée.` / `This room could not be found or has been closed.`                     |
| Settings changed by a participant who is not the admin | 403  | `room_admin_required`                                                                   | `Seul le room admin peut faire cela.` / `Only the room admin can do this.`                                              |
| Setting other than late arrivals during a game         | 409  | `room_settings_locked`                                                                  | `Pendant une partie, seules les arrivées peuvent être modifiées.` / `During a game, only late arrivals can be changed.` |
| Duration out of bounds                                 | 422  | `validation_error`, field `greater_than_equal` / `less_than_equal` (params `ge` / `le`) | `Au moins {{ge}}.` / `At least {{ge}}.`, `Au plus {{le}}.` / `At most {{le}}.`                                          |
| Unknown setting value                                  | 422  | `validation_error`                                                                      | `Certains champs sont invalides.` / `Some fields are invalid.`                                                          |
| Missing or invalid access token                        | 401  | `not_authenticated`                                                                     | Handled by the API client: refresh of the session, otherwise back to `/login`                                           |

## 2. Technical design

### 2.1 Options considered

| Topic        | Options                                                      | Choice and reason                                                                                                                                                                          |
| ------------ | ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Settings     | Separate `room_settings` table (1-1); **columns of `rooms`** | **Columns**: the domain model makes them a 1-1 composition of the room; columns avoid a join and an orphan row. The API still groups them in a `settings` object.                          |
| Game lock    | Wait for the games (#91); **`status` open / playing now**    | **Status now**: the "locked during a game" rule is built and tested with the settings; the game start (#91) only sets `playing`. "Closed" is not a status: a closed room is deleted (#89). |
| Code         | Sequential; UUID; **short random code**                      | **Short random code**: typed or dictated by players, impossible to guess from other codes. A unique constraint and a new draw on collision keep it unique.                                 |
| Admin's seat | Role only in `rooms.admin_id`; **participant row too**       | **Participant row**: the admin counts in the participant limit even when not playing (US-2.6), and their seat gives access like any other participant.                                     |
| Addressing   | By UUID; **by code**                                         | **By code**: the [real-time guide](realtime.md) addresses the room channel and its REST snapshot by code (`/rooms/{code}`).                                                                |

### 2.2 Data model

```
users ──< rooms ──< participants >── users
            │
            └──> templates (SET NULL)
```

| Table          | Columns                                                                                                                                                                                                            | Notes                                                                                                                                                                                                                                        |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `rooms`        | `id`, `code` (6, unique), `admin_id` → `users`, `template_id` → `templates` (nullable), `status`, `item_order`, `auto_advance`, `timer_seconds`, `cooldown_seconds`, `admin_plays`, `late_arrivals_allowed`, dates | `ON DELETE CASCADE` towards `users`, `ON DELETE SET NULL` towards `templates`; indexes on `admin_id` and `template_id`. `status`, `item_order`, `auto_advance`: text columns with a `CHECK` constraint (`ck_rooms_*`), like `images.status`. |
| `participants` | `id`, `room_id` → `rooms`, `user_id` → `users`, dates                                                                                                                                                              | `ON DELETE CASCADE` towards both. Unique `(room_id, user_id)`: one seat per user and room (invariant 10); it also serves as the index on `room_id`. Index on `user_id`.                                                                      |

The neighbouring issues add their own columns: `connected` and the room version for real time (#85), the guest fields (#87, `user_id` becomes nullable), and #89 will keep the participants of past games when a room closes.

### 2.3 Code generation

`generate_room_code()` (`app/services/rooms.py`) draws `ROOM_CODE_LENGTH` characters of `ROOM_CODE_ALPHABET` with `secrets.choice`. `RoomService.create` inserts the room in a **savepoint** (`session.begin_nested()`): when the insert breaks the unique constraint `uq_rooms_code`, only the savepoint is rolled back and a new code is drawn, up to `ROOM_CODE_MAX_ATTEMPTS` (5) times. With 32^6 (about a billion) codes, a single collision is already rare; reaching the limit is logged as an error and answers `500`. Any other integrity error is raised as is.

### 2.4 Settings

| Variable                        | Purpose                                              | Default |
| ------------------------------- | ---------------------------------------------------- | ------- |
| `ROOM_DEFAULT_TIMER_SECONDS`    | Timer per item of a new room, in seconds (5 to 300)  | `30`    |
| `ROOM_DEFAULT_COOLDOWN_SECONDS` | Final cooldown of a new room, in seconds (10 to 600) | `60`    |

The bounds are constants (`app/constants/rooms.py`): the API validates the durations with them and returns them as `ge` / `le` params, which the frontend displays without copying them. The defaults are validated against the same bounds when the application starts.

### 2.5 Endpoints

Every route requires the Bearer access token (`401` otherwise).

| Method and path                | Body                                                                                                    | Success              | Errors                            |
| ------------------------------ | ------------------------------------------------------------------------------------------------------- | -------------------- | --------------------------------- |
| `POST /rooms`                  | `{template_id}`                                                                                         | `201` `RoomResponse` | `401`, `404`, `409`, `422`        |
| `GET /rooms/{code}`            | —                                                                                                       | `200` `RoomResponse` | `401`, `404`                      |
| `PATCH /rooms/{code}/settings` | `{item_order?, auto_advance?, timer_seconds?, cooldown_seconds?, admin_plays?, late_arrivals_allowed?}` | `200` `RoomResponse` | `401`, `403`, `404`, `409`, `422` |

- `RoomResponse` is `{code, link, status, template: {id, name} | null, settings: {item_order, auto_advance, timer_seconds, cooldown_seconds, admin_plays, late_arrivals_allowed}, participants: [{id, display_name, is_admin}], is_admin}`. `participants` are in order of arrival, the room admin first; `is_admin` says whether the user making the request is the room admin.
- `PATCH /rooms/{code}/settings` locks the room row (`SELECT … FOR UPDATE`) until its commit, as the [real-time guide](realtime.md) requires for every change of a room.

### 2.6 Known limitations

- Only the room admin has a seat: joining with an account (#86) or as a guest (#87) comes later, as well as the participant limit (#88).
- No live updates yet: the room channel and the presence come with #85; until then the lobby is read again when the tab gets the focus back.
- No game yet: the game start (#91) sets `playing` and freezes the template (`take_snapshot`, [templates guide](templates.md) §2.4).
- Closing a room (#89) and closing it automatically when inactive (#90) come later.

## 3. In the code

### Backend (`backend/app/`)

| Layer         | File                                                                      | Content                                                                                                                                                                                                                     |
| ------------- | ------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Routes        | `api/routes/rooms.py`                                                     | The `/rooms` routes; map the domain exceptions to `404` `template_not_found` / `room_not_found`, `409` `template_has_no_tiles` / `room_settings_locked`, `403` `room_admin_required`; `_room_response` builds the response. |
| Dependencies  | `api/dependencies.py`                                                     | `get_room_service`.                                                                                                                                                                                                         |
| Schemas       | `schemas/rooms.py`                                                        | `CreateRoomRequest`, `UpdateRoomSettingsRequest` (`TimerSeconds`, `CooldownSeconds` with their bounds), `RoomSettingsResponse`, `RoomTemplateResponse`, `ParticipantResponse`, `RoomResponse`.                              |
| Service       | `services/rooms.py`                                                       | `generate_room_code`; `RoomService`: `create` (new draw on collision, `_insert_unless_code_taken`), `get`, `update_settings` (locked), `link`. Owns the transactions (`commit`).                                            |
| Repository    | `repositories/rooms.py`                                                   | `add_room`, `get_room_by_code` (with the template and the participants, locked with `for_update`).                                                                                                                          |
| Models        | `models/room.py`, `models/participant.py`                                 | `Room` with `RoomStatus`, `ItemOrder`, `AutoAdvance`; `Participant`.                                                                                                                                                        |
| Exceptions    | `exceptions/rooms.py`                                                     | `RoomNotFoundError`, `RoomAdminRequiredError`, `RoomSettingsLockedError`; `TemplateHasNoTilesError` comes from `exceptions/templates.py`.                                                                                   |
| Constants     | `constants/rooms.py`, `constants/error_codes.py`, `constants/messages.py` | Code length and alphabet, `ROOM_CODE_MAX_ATTEMPTS`, `FRONTEND_ROOM`, duration bounds; the codes `ROOM_NOT_FOUND`, `ROOM_ADMIN_REQUIRED`, `ROOM_SETTINGS_LOCKED` and their developer messages.                               |
| Configuration | `core/config.py`                                                          | `ROOM_DEFAULT_TIMER_SECONDS`, `ROOM_DEFAULT_COOLDOWN_SECONDS`.                                                                                                                                                              |
| Migration     | `migrations/versions/fedf7b56dfa2_create_rooms_and_participants.py`       | Creates the two tables.                                                                                                                                                                                                     |

### Frontend (`frontend/src/`)

Built in #84.

| Layer        | File                                        | Content                                                                                                                                                                                                                                                                                                                                                                            |
| ------------ | ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| API          | `api/rooms.ts`                              | `useCreateRoom` (`POST /rooms`), `useRoom` (`GET /rooms/{code}`), `useUpdateRoomSettings` (`PATCH /rooms/{code}/settings`). The room returned by a creation or a change replaces the cached one (`roomQueryKey(code)`), so the lobby shows it without a new request.                                                                                                               |
| Constants    | `constants/rooms.ts`, `constants/routes.ts` | `ROOMS_QUERY_KEY`, `roomQueryKey`; `ROUTES.ROOM` (`/r/:code`, the format of the shared link, `FRONTEND_ROOM` on the backend) and `roomPath(code)`. The duration bounds are not copied: the form shows the `ge` / `le` params of the `422`.                                                                                                                                         |
| Button       | `components/CreateRoomButton.tsx`           | "Create a room", on each row of _My templates_ and next to the title of the template editor. Creates the room with the default settings, then opens its lobby; shows the translated error (`template_has_no_tiles`, `template_not_found`).                                                                                                                                         |
| Page         | `pages/RoomPage.tsx`                        | `/r/:code`, signed in only (`RequireAuth`): title, template name (or a notice when it was purged), "Game in progress" notice, `RoomInvite`, participants (the room admin marked), settings summary and, for the room admin, `RoomSettingsDialog`. Loading and error states (`room_not_found` for an unknown code or a user without a seat).                                        |
| Components   | `components/RoomInvite.tsx`                 | The code in large type and the link in a read-only field; "Copy link" uses `navigator.clipboard` and announces "Link copied" in an `aria-live` area, or asks to copy by hand when the clipboard refuses.                                                                                                                                                                           |
|              | `components/RoomSettingsSummary.tsx`        | The five settings in plain words, for every participant.                                                                                                                                                                                                                                                                                                                           |
|              | `components/RoomSettingsDialog.tsx`         | Native `<dialog>` opened by "Edit": radios (item order, next item), number fields (timer, cooldown), checkboxes (admin plays, late arrivals). The timer duration is enabled and sent only with the timer. During a game, every field but late arrivals is disabled and only late arrivals are sent. The form is remounted at each opening, so it starts from the current settings. |
| Translations | `i18n/locales/fr.ts`, `en.ts`               | `rooms.create.*`, `rooms.lobby.*`, `rooms.settings.*` (with `rooms.settings.summary.*`), `errors.api.{room_not_found, room_admin_required, room_settings_locked}` and `errors.field.{greater_than_equal, less_than_equal}`.                                                                                                                                                        |

No live updates before #85: the lobby relies on the default refetch of TanStack Query (when the tab gets the focus back). Joining from the link when one has no seat is #86.

### Tests

`backend/tests/integration/test_rooms.py` (endpoints, against a real PostgreSQL) and `backend/tests/test_room_codes.py` (code generator); `frontend/src/pages/RoomPage.test.tsx`, `components/RoomSettingsDialog.test.tsx`, and the room creation in `TemplatesPage.test.tsx` / `TemplateEditorPage.test.tsx`. All are described in the [testing guide](testing.md).
