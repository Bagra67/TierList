# Games

English | [Français](games.fr.md)

How a game is played in a room: its start, its rounds and, later, its placements, its cooldown and its closing. **Built in #91** for the start; placements (#92), the round progression and timers (#93), the game screen (#94), reconnection (#95), the cooldown (#96) and the closing (#98) come next.

## 1. Functional overview

The room admin starts a game from the lobby (US-3.1). The game is frozen on the current version of the template, the item order is fixed, and the first item is shown to everyone.

| Action       | Endpoint                  | Result                                                                                                                               |
| ------------ | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Start a game | `POST /rooms/{code}/game` | The room in `playing`, with its game: round 1 of N, the current item (text and/or image) and the end of its timer when there is one. |

### Rules

- **Who**: the room admin only (`403` `room_admin_required`); a reader without a seat gets `404` `room_not_found`, like every room route.
- **One game at a time** (invariant 3): a room already `playing` answers `409` `game_in_progress`. A partial unique index on `games(room_id)` (`status <> 'closed'`) is the last safety net.
- **Someone must place the items** (US-3.1, US-3.5): the placing participants are the seated participants, minus the room admin when they do not play (`admin_plays` off); they keep only the controls. Without any, `409` `no_placing_participant` (the room admin alone, not playing). Being connected is not required: a participant who is not there gets absent votes, like in any round (#93).
- **Template**: the template of the room must still exist and have tiles. A purged template answers `409` `template_not_found`, a template without tiles `409` `template_has_no_tiles`.
- **Frozen version** (invariant 4): `take_snapshot` ([templates guide](templates.md#24-snapshots-template-versions)) copies the tiers and tiles; editing the template afterwards never changes the game.
- **Item order** (invariant 5): the snapshot tiles in template order, or shuffled when `item_order` is `random`. One round per tile, numbered from 1.
- **First round**: started at once; with `auto_advance = timer`, its end (`ends_at`) is now + `timer_seconds`.
- **Settings kept with the game**: `item_order` and `admin_plays`, so that they stay known once the room is closed (the results exclude the room admin who did not play).

### Messages

| Situation                                        | HTTP            | API code                                                     | Translation (FR / EN)                                                                                                                                                                           |
| ------------------------------------------------ | --------------- | ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A game is already in progress                    | 409             | `game_in_progress`                                           | `Une partie est déjà en cours dans cette salle.` / `A game is already in progress in this room.`                                                                                                |
| Nobody would place the items                     | 409             | `no_placing_participant`                                     | `Il faut au moins un participant qui place les items : invitez un joueur ou jouez vous-même.` / `A game needs at least one participant who places the items: invite a player or play yourself.` |
| Template purged, or without tiles                | 409             | `template_not_found`, `template_has_no_tiles`                | Existing translations ([templates guide](templates.md))                                                                                                                                         |
| Not the room admin / no seat / not authenticated | 403 / 404 / 401 | `room_admin_required`, `room_not_found`, `not_authenticated` | Existing translations ([rooms guide](rooms.md#messages))                                                                                                                                        |

## 2. Technical design

### 2.1 Data model

```
rooms ──< games (room_id SET NULL) ──< rounds >── snapshot_tiles
             └──> template_snapshots
```

| Table    | Columns                                                                                                                                                                     | Notes                                                                                                                                                                                                                           |
| -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `games`  | `id`, `room_id` → `rooms` (nullable), `snapshot_id` → `template_snapshots`, `status`, `item_order`, `admin_plays`, `current_round_number`, `started_at`, `closed_at`, dates | `ON DELETE SET NULL` towards `rooms`: a game **outlives** its room (invariant 11). `status`: `in_round`, `cooldown`, `closed` (text column with a `CHECK`, like the room). Partial unique index `uq_games_room_id_in_progress`. |
| `rounds` | `id`, `game_id` → `games`, `number`, `snapshot_tile_id` → `snapshot_tiles`, `started_at`, `ends_at`, `ended_at`                                                             | `ON DELETE CASCADE` towards `games`. Unique `(game_id, number)` and `(game_id, snapshot_tile_id)`: one round per tile. A round points at a **snapshot** tile, never at a template tile.                                         |

All the rounds are created at the start; only round 1 has `started_at`. `ends_at` is the timer end (server time, UTC), `ended_at` the actual end (#93).

### 2.2 Start

`GameService.start` (`app/services/games.py`) runs in **one transaction**:

1. Locks the room (`RoomService.get_for_change`), checks the room admin, the status, the template and the placing participants.
2. `TemplateService.take_snapshot` locks the template and only flushes.
3. Orders the snapshot tiles (`shuffle_items`, `random.SystemRandom`, for `random`), creates the game and its rounds, starts round 1.
4. Sets the room `playing`, increments `rooms.version`, commits.
5. **After the commit**, publishes `game.started` (`{round_number, round_count, ends_at}`) to the room ([real-time guide](realtime.md)).

The timer end is **stored but not acted on yet**: ending the round when time is up, and re-scheduling the deadlines at startup, come with #93 ([real-time guide](realtime.md#28-server-side-timers)).

### 2.3 What the room returns

`RoomResponse.game` is the game in progress, `null` outside a game:

```json
{
  "round_number": 1,
  "round_count": 12,
  "current_item": {
    "id": "…",
    "text": "Paprika",
    "image_url": "https://…/x.webp"
  },
  "ends_at": null
}
```

The current item is shown to every participant: it is not a secret. Other participants' placements are never sent (private board, #92). The room routes take the image storage (`get_image_storage`) to build the public image URL, like the template routes.

## 3. In the code

### Backend (`backend/app/`)

| Layer        | File                                                                                    | Content                                                                                                                                                                                                                                                                                               |
| ------------ | --------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Route        | `api/routes/rooms.py`                                                                   | `start_game` (`POST /rooms/{code}/game`, `201`); `_current_game_response` builds `RoomResponse.game`.                                                                                                                                                                                                 |
| Dependencies | `api/dependencies.py`                                                                   | `get_game_service`.                                                                                                                                                                                                                                                                                   |
| Service      | `services/games.py`                                                                     | `GameService.start`, `placing_participants`, `shuffle_items` (replaced in the tests).                                                                                                                                                                                                                 |
| Models       | `models/game.py`, `models/round.py`, `models/room.py`, `models/enums.py`, `db/types.py` | `Game`, `GameStatus`, `current_round`; `Round`; `Room.current_game` (read-only relationship filtered on `status <> 'closed'`); `ItemOrder` and `AutoAdvance` (`models/enums.py`), settings shared by the room and the game; `text_enum` (`db/types.py`), the text column with a `CHECK` used by both. |
| Repository   | `repositories/rooms.py`                                                                 | `get_room_by_code` also loads the game in progress, its rounds and their tile.                                                                                                                                                                                                                        |
| Schemas      | `schemas/rooms.py`, `schemas/room_events.py`                                            | `CurrentGameResponse`, `CurrentItemResponse`; `GameStartedEvent`.                                                                                                                                                                                                                                     |
| Errors       | `exceptions/games.py`, `constants/error_codes.py`, `constants/messages.py`              | `GameInProgressError`, `NoPlacingParticipantError`; `GAME_IN_PROGRESS`, `NO_PLACING_PARTICIPANT`.                                                                                                                                                                                                     |
| Migration    | `migrations/versions/5f588806f8ee_create_games_and_rounds.py`                           | Creates `games` and `rounds`.                                                                                                                                                                                                                                                                         |

### Frontend (`frontend/src/`)

| Layer        | File                             | Content                                                                                                                                        |
| ------------ | -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| API          | `api/rooms.ts`                   | `useStartGame` (`POST /rooms/{code}/game`); the returned room replaces the cached one.                                                         |
| Components   | `components/StartGameButton.tsx` | "Start the game", for the room admin outside a game; translated errors.                                                                        |
|              | `components/RoomLobby.tsx`       | During a game: "Game in progress", "Item n of N" and the current item (text, image with its `alt`). Temporary: the game screen comes with #94. |
| Real time    | `api/roomChannel.ts`             | `game.started` reads the room again (default behaviour).                                                                                       |
| Translations | `i18n/locales/fr.ts`, `en.ts`    | `rooms.lobby.start.*`, `rooms.lobby.currentItem`, `rooms.lobby.currentItemImage`, `errors.api.{game_in_progress, no_placing_participant}`.     |

### Tests

`backend/tests/integration/test_game_start.py`; `frontend/src/components/StartGameButton.test.tsx` and the game in progress in `pages/RoomPage.test.tsx`. All are described in the [testing guide](testing.md).

## 4. Known limitations

- The round never ends yet: no placements (#92), no "next", timer or "everyone placed" (#93).
- What happens to a removed participant's placements is decided with the placements (#92).
- Closing a room during a game (#89) will have to close the game first (#98).
- "A game is in progress" lives in two places: `rooms.status = playing` and a `games` row not `closed`. The start writes both in one transaction, under the room lock; the closing (#98) must set the room back to `open` in the same transaction as the game.
