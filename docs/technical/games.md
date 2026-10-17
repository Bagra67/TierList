# Games

English | [Français](games.fr.md)

How a game is played in a room: its start, its rounds, its placements, the move to the next round and, later, its cooldown and its closing. **Built in #91** for the start, **#92** for the placements and **#93** for the round progression (next, timer, everyone placed, absent votes) **#94** for the game screen and **#95** for coming back to one's seat and joining during a game; the cooldown with the final placements (#96) and the closing (#98) come next.

## 1. Functional overview

The room admin starts a game from the lobby (US-3.1). The game is frozen on the current version of the template, the item order is fixed, and the first item is shown to everyone. Each participant who places drops the current item in a tier, at the position they want (US-3.3), on a **private board**: the others only see who has placed it.

| Action                 | Endpoint                                      | Result                                                                                                                                                                     |
| ---------------------- | --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Start a game           | `POST /rooms/{code}/game`                     | The room in `playing`, with its game: round 1 of N, the current item (text and/or image) and the end of its timer when there is one.                                       |
| Place the current item | `PUT /rooms/{code}/game/placements/{tile_id}` | Body `{tier_id, position}`. The room, with the reader's board updated (`own_placements`) and who has placed the current item. Placing it again in the same round moves it. |
| Next item              | `POST /rooms/{code}/game/next`                | Room admin only. Ends the round in progress and shows the next item to everyone, or starts the final cooldown after the last item.                                         |

### Rules

- **Who**: the room admin only (`403` `room_admin_required`); a reader without a seat gets `404` `room_not_found`, like every room route.
- **One game at a time** (invariant 3): a room already `playing` answers `409` `game_in_progress`. A partial unique index on `games(room_id)` (`status <> 'closed'`) is the last safety net.
- **Someone must place the items** (US-3.1, US-3.5): the placing participants are the seated participants, minus the room admin when they do not play (`admin_plays` off); they keep only the controls. Without any, `409` `no_placing_participant` (the room admin alone, not playing). Being connected is not required: a participant who is not there gets absent votes, like in any round (#93).
- **Template**: the template of the room must still exist and have tiles. A purged template answers `409` `template_not_found`, a template without tiles `409` `template_has_no_tiles`.
- **Frozen version** (invariant 4): `take_snapshot` ([templates guide](templates.md#24-snapshots-template-versions)) copies the tiers and tiles; editing the template afterwards never changes the game.
- **Item order** (invariant 5): the snapshot tiles in template order, or shuffled when `item_order` is `random`. One round per tile, numbered from 1.
- **First round**: started at once; with `auto_advance = timer`, its end (`ends_at`) is now + `timer_seconds`.
- **Settings kept with the game**: `item_order` and `admin_plays`, so that they stay known once the room is closed (the results exclude the room admin who did not play).
- **Who places** (US-3.3, US-3.5): every placing participant, account or guest (the guest with the cookie of the room); the room admin who does not play gets `403` `not_a_placing_participant`.
- **Only the current item** (US-3.3): the tile must be the item of the current round, otherwise `409` `item_not_current` (an item of a past round cannot move before the cooldown, a future one is not shown yet). Outside a round (no game, or later the cooldown), `409` `round_not_in_progress`. The tier must be one of the game's frozen version, otherwise `404` `tier_not_found`.
- **Tier and position**: positions start at `0` and stay **continuous** in each tier, per participant: placing at `k` shifts the next items, a position past the end puts the item last, and the tier it leaves closes up. The relative order of past items never changes. Placing the item again in the same round replaces its placement (invariant 6: one round placement per tile).
- **Private board**: the response only holds the reader's own placements; the others' are never sent, only **who** has placed the current item (`placed_participant_ids`).
- **Removed participant**: their placements are deleted with their seat; they are no longer in the game nor in its results.
- **Next item** (US-3.4): the room admin ends the round at any time, whatever the automatic setting and even if some have not placed; a player gets `403` `room_admin_required`, and outside a round (no game, cooldown) `409` `round_not_in_progress`.
- **Timer** (`auto_advance = timer`): each round ends at its `ends_at` (start + `timer_seconds`), decided by the server alone.
- **Everyone placed** (`auto_advance = everyone_placed`): the round ends when every **connected** placing participant has placed the current item. A disconnected participant is not waited for; at least one placing participant must be connected (nobody connected never ends the round). It is checked after a first placement, a departure (end of the grace delay) and a removal.
- **Absent votes** (US-4.3): when a round ends, every placing participant without a round placement for the item gets an absent vote (no tier, no position), connected or not.
- **Late arrival** (US-4.5): a participant who joins during a game gets an absent vote for every round already over, and places from the current round.
- **Coming back** (US-4.4): a participant who loses the connection keeps their seat and their board; the rounds that end meanwhile give them absent votes. They come back through `POST /join` (account), the room cookie (guest, same browser) or the personal link (guest, any device), even when arrivals are locked or the room is full. The room they get holds their board (`own_placements`) and the current round, and the real-time channel reconnects then reads the room again ([real-time guide](realtime.md)).
- **Last round**: when it ends, the game moves to `cooldown`; its end (`cooldown_ends_at`) is now + `cooldown_seconds`. What happens during and after the cooldown comes with #96.

### Messages

| Situation                                        | HTTP            | API code                                                     | Translation (FR / EN)                                                                                                                                                                           |
| ------------------------------------------------ | --------------- | ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A game is already in progress                    | 409             | `game_in_progress`                                           | `Une partie est déjà en cours dans cette salle.` / `A game is already in progress in this room.`                                                                                                |
| Nobody would place the items                     | 409             | `no_placing_participant`                                     | `Il faut au moins un participant qui place les items : invitez un joueur ou jouez vous-même.` / `A game needs at least one participant who places the items: invite a player or play yourself.` |
| The room admin does not play                     | 403             | `not_a_placing_participant`                                  | `Vous ne jouez pas cette partie : vous avez seulement les commandes.` / `You do not play in this game: you only have the controls.`                                                             |
| The tile is not the current item                 | 409             | `item_not_current`                                           | `Cet item n'est plus l'item en cours : le tour est passé.` / `This item is no longer the current one: the round has moved on.`                                                                  |
| No round in progress                             | 409             | `round_not_in_progress`                                      | `Aucun tour n'est en cours : l'item ne peut plus être placé.` / `No round is in progress: the item can no longer be placed.`                                                                    |
| Tier outside the game                            | 404             | `tier_not_found`                                             | Existing translation ([templates guide](templates.md))                                                                                                                                          |
| Template purged, or without tiles                | 409             | `template_not_found`, `template_has_no_tiles`                | Existing translations ([templates guide](templates.md))                                                                                                                                         |
| Not the room admin / no seat / not authenticated | 403 / 404 / 401 | `room_admin_required`, `room_not_found`, `not_authenticated` | Existing translations ([rooms guide](rooms.md#messages))                                                                                                                                        |

## 2. Technical design

### 2.1 Data model

```
rooms ──< games (room_id SET NULL) ──< rounds >── snapshot_tiles
             ├──> template_snapshots
             └──< placements >── participants (CASCADE), snapshot_tiles, snapshot_tiers
```

| Table        | Columns                                                                                                                                                                                         | Notes                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `games`      | `id`, `room_id` → `rooms` (nullable), `snapshot_id` → `template_snapshots`, `status`, `item_order`, `admin_plays`, `current_round_number`, `started_at`, `cooldown_ends_at`, `closed_at`, dates | `ON DELETE SET NULL` towards `rooms`: a game **outlives** its room (invariant 11). `status`: `in_round`, `cooldown`, `closed` (text column with a `CHECK`, like the room). Partial unique index `uq_games_room_id_in_progress`.                                                                                                                                                                                                                        |
| `rounds`     | `id`, `game_id` → `games`, `number`, `snapshot_tile_id` → `snapshot_tiles`, `started_at`, `ends_at`, `ended_at`                                                                                 | `ON DELETE CASCADE` towards `games`. Unique `(game_id, number)` and `(game_id, snapshot_tile_id)`: one round per tile. A round points at a **snapshot** tile, never at a template tile.                                                                                                                                                                                                                                                                |
| `placements` | `id`, `game_id` → `games`, `participant_id` → `participants`, `snapshot_tile_id` → `snapshot_tiles`, `phase`, `snapshot_tier_id` → `snapshot_tiers` (nullable), `position` (nullable), dates    | `ON DELETE CASCADE` towards `games` and `participants`. `phase`: `round` or `final` (#96). Unique `(game_id, participant_id, snapshot_tile_id, phase)` (invariant 6). `ck_placements_tier_and_position`: a tier and a position `>= 0`, or neither for an **absent** vote (invariant 8, #93); `ck_placements_final_not_absent`. No unique constraint on the position: shifting the next items would break it midway, the service keeps them continuous. |

All the rounds are created at the start; only round 1 has `started_at`. `ends_at` is the timer end (server time, UTC), `ended_at` the actual end (#93).

### 2.2 Start

`GameService.start` (`app/services/games.py`) runs in **one transaction**:

1. Locks the room and checks the room admin (`RoomService.get_for_admin_change`), then the status, the template and the placing participants.
2. `TemplateService.take_snapshot` locks the template and only flushes.
3. Orders the snapshot tiles (`shuffle_items`, `random.SystemRandom`, for `random`), creates the game and its rounds, starts round 1.
4. Sets the room `playing`, increments `rooms.version`, commits.
5. **After the commit**, publishes `game.started` (`{round_number, round_count, ends_at}`) to the room ([real-time guide](realtime.md)).

The timer end is **stored but not acted on yet**: ending the round when time is up, and re-scheduling the deadlines at startup, come with #93 ([real-time guide](realtime.md#28-server-side-timers)).

### 2.3 What the room returns

`RoomResponse.game` is the game in progress **seen by the reader**, `null` outside a game:

```json
{
  "round_number": 1,
  "round_count": 12,
  "current_item": {
    "id": "…",
    "text": "Paprika",
    "image_url": "https://…/x.webp"
  },
  "ends_at": null,
  "tiers": [{ "id": "…", "name": "S", "color": "#FF7F7F" }],
  "placed_participant_ids": ["…"],
  "own_placements": [
    {
      "item": { "id": "…", "text": "Chorizo", "image_url": null },
      "tier_id": "…",
      "position": 0
    }
  ]
}
```

The current item and the frozen tiers (top to bottom) are shown to every participant. `placed_participant_ids` says **who** has placed the current item, never where. `own_placements` holds the reader's round placements only, sorted by tier then position, so a participant who comes back finds their board; it is empty for the room admin who does not play. The response is built for the reader's **seat** (`room_response(room, seat, …)`): the routes find it with `RoomService.seat_of` (account or guest cookie) or `seat_in` (an account in a room already read). The room routes take the image storage (`get_image_storage`) to build the public image URLs (`optional_image_url`).

### 2.4 Placements

`GameService.place` (`app/services/games.py`) runs in **one transaction**:

1. Finds the reader's seat and **locks the room** (`RoomService.seat_of(viewer, code, for_update=True)`): two placements in the same room run one after the other.
2. Checks the round in progress, that the seat places (`placing_participants`), the current item and the tier.
3. Works on the reader's board for the round phase: takes the placement of the tile out of its tier if it exists, inserts it at the position (bounded to the end of the tier) and renumbers both tiers `0..n-1` (`_place_in_tier`).
4. **First placement of the round**: increments `rooms.version`, commits, then publishes `participant.placed` (`{participant_id, round_number}`, no tier nor position). **A move** commits without a new version nor event: the others see nothing change.

Absent votes are created when a round ends (§2.5); final placements (cooldown) come with #96.

### 2.5 Round progression

Three triggers end a round, and all of them run the same transition, `GameService._end_round`, **under the room lock**:

| Trigger         | Entry point                                                                                                                                     | Checked state                                                                                    |
| --------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| "Next item"     | `POST /rooms/{code}/game/next` → `next_round` (room admin, `get_for_admin_change`)                                                              | A round in progress, otherwise `409`.                                                            |
| Timer           | `RoundTimers` → `end_round_on_timer(game_id, round_number)`                                                                                     | The same round still in progress, otherwise nothing.                                             |
| Everyone placed | `place` (same transaction), `advance_if_everyone_placed(room_id)` after a departure (`routes/room_channel.py`) or a removal (`routes/rooms.py`) | `_everyone_placed`: the setting, at least one connected placing participant, all of them placed. |

`_end_round` sets `ended_at`, adds the absent votes, then either starts the next round (`started_at`, and `ends_at` with a timer) or moves the game to `cooldown` with `cooldown_ends_at`; it increments `rooms.version`. After the commit, the service publishes `round.started` (`{round_number, round_count, ends_at}`) or `cooldown.started` (`{ends_at}`), and schedules the timer of the new round.

**Races**: the timer, "next" and the last placement may arrive together. Each one locks the room and checks the expected state first; the second one finds the round over and does nothing. Transitions are therefore **idempotent**, and a round ended early does not need its timer cancelled.

**Server-side timers** (`services/round_timers.py`, [real-time guide](realtime.md#28-server-side-timers)): `RoundTimers` keeps one `asyncio` task per game, which waits for the `ends_at` of its current round and then calls `end_round_on_timer` through the threadpool, in a short session. `schedule` is thread-safe (`call_soon_threadsafe`, called from the REST routes after the commit); a new deadline for the same game replaces the previous one; a deadline already passed fires at once. At startup (`lifespan` in `main.py`), `pending_round_deadlines` reads the rounds in progress that wait for their timer and schedules them again: a restart loses no timer. The services receive it through the `RoundScheduler` protocol (`get_round_scheduler`), replaced by a recording fake in the tests.

**Late arrival**: `RoomService.join` and `join_as_guest` call `_absent_for_past_rounds` in the same transaction as the new seat.

## 3. In the code

### Backend (`backend/app/`)

| Layer        | File                                                                                                           | Content                                                                                                                                                                                                                                                                                                                                                                    |
| ------------ | -------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Route        | `api/routes/rooms.py`                                                                                          | `start_game` (`POST /rooms/{code}/game`, `201`), `place_item` (`PUT /rooms/{code}/game/placements/{tile_id}`, `200`, accounts and guests), `next_round` (`POST /rooms/{code}/game/next`, `200`); `remove_participant` then calls `advance_if_everyone_placed`.                                                                                                             |
|              | `api/routes/room_channel.py`, `main.py`                                                                        | `_set_presence`: a departure during a game calls `advance_if_everyone_placed`. `lifespan`: starts `round_timers`, schedules the pending deadlines again (`_reschedule_rounds`), stops the timers at shutdown.                                                                                                                                                              |
| Presenters   | `api/presenters/rooms.py`                                                                                      | `room_response(room, seat, …)`, built for the reader's seat; `current_game_response` builds `RoomResponse.game` (tiers, who placed, own placements); `_item_response`.                                                                                                                                                                                                     |
| Dependencies | `api/dependencies.py`                                                                                          | `get_game_service`, `get_round_scheduler` (`RoundSchedulerDep`).                                                                                                                                                                                                                                                                                                           |
| Service      | `services/games.py`                                                                                            | `GameService.start`, `next_round`, `end_round_on_timer`, `advance_if_everyone_placed`, `pending_round_deadlines`, `_end_round`, `_everyone_placed`, `place` (`_place_in_tier`, `_in_tier`, `_renumber`), `placing_participants`, `shuffle_items` (replaced in the tests). Receives `RoomService` and `TemplateService` from `get_game_service`, on the same session.       |
|              | `services/rooms.py`                                                                                            | `seat_of(viewer, code, for_update)`: the reader's seat (account or guest), its room locked when needed; `seat_in(room, user)`; `_absent_for_past_rounds` (late arrival); `set_presence` returns the room when the presence changed.                                                                                                                                        |
|              | `services/round_timers.py`                                                                                     | `RoundScheduler` (protocol), `RoundTimers` (`start`, `schedule`, `stop`), the process singleton `round_timers`.                                                                                                                                                                                                                                                            |
| Models       | `models/game.py`, `models/round.py`, `models/placement.py`, `models/room.py`, `models/enums.py`, `db/types.py` | `Game`, `current_round`, `placements`; `Round`; `Placement`, `is_absent`; `Room.current_game` (read-only relationship filtered on `status <> 'closed'`); `GameStatus`, `RoomStatus`, `ItemOrder`, `AutoAdvance` and `PlacementPhase` (`models/enums.py`), shared by the models, the schemas and the services; `text_enum` (`db/types.py`), the text column with a `CHECK`. |
| Repository   | `repositories/rooms.py`, `repositories/games.py`                                                               | `get_room_by_code` and `get_room_by_id` load the room with its game in progress, its rounds and their tile, its frozen tiers and its placements (`_room_with_details`); `add_game`, `get_room_id_of_game`, `list_pending_round_deadlines`.                                                                                                                                 |
| Schemas      | `schemas/rooms.py`, `schemas/room_events.py`                                                                   | `CurrentGameResponse`, `CurrentItemResponse`, `GameTierResponse`, `OwnPlacementResponse`, `PlaceItemRequest`; `GameStartedEvent`, `ParticipantPlacedEvent`, `RoundStartedEvent`, `CooldownStartedEvent`; `CurrentGameResponse.status` and `cooldown_ends_at`.                                                                                                              |
| Errors       | `exceptions/games.py`, `constants/error_codes.py`, `constants/messages.py`                                     | `GameInProgressError`, `NoPlacingParticipantError`, `RoundNotInProgressError`, `NotAPlacingParticipantError`, `ItemNotCurrentError`; the matching codes; `TierNotFoundError` comes from `exceptions/templates.py`.                                                                                                                                                         |
| Migration    | `migrations/versions/5f588806f8ee_create_games_and_rounds.py`                                                  | Creates `games` and `rounds`.                                                                                                                                                                                                                                                                                                                                              |
|              | `migrations/versions/e1bf9bc677cd_create_placements.py`                                                        | Creates `placements`.                                                                                                                                                                                                                                                                                                                                                      |
|              | `migrations/versions/eaab3dece658_add_cooldown_ends_at_to_games.py`                                            | Adds `games.cooldown_ends_at`.                                                                                                                                                                                                                                                                                                                                             |

### Frontend (`frontend/src/`)

| Layer        | File                                                                                   | Content                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ------------ | -------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| API          | `api/rooms.ts`                                                                         | `useStartGame` (`POST /rooms/{code}/game`), `usePlaceItem` (`PUT …/placements/{tile_id}`), `useNextRound` (`POST …/game/next`); the returned room replaces the cached one.                                                                                                                                                                                                                                                                                                                                      |
| Components   | `components/StartGameButton.tsx`                                                       | "Start the game", for the room admin outside a game; translated errors.                                                                                                                                                                                                                                                                                                                                                                                                                                         |
|              | `components/RoomLobby.tsx`                                                             | During a game, shows `GameScreen` at the top; the participants, the invitation and the settings stay below.                                                                                                                                                                                                                                                                                                                                                                                                     |
|              | `components/GameScreen.tsx`                                                            | The game screen (US-3.2 to US-3.5): the current item (`GameItemView`), "Item n of N", the round countdown (`Countdown`), who has placed (`PlacedList`), the reader's board if they place, the room admin's controls; the final cooldown with its countdown. The placing participants are all of them, minus the room admin who does not play; `is_you` finds the reader.                                                                                                                                        |
|              | `components/GameBoard.tsx`                                                             | The private board: one row per tier with the items already placed (they do not move), the current item to drop. dnd-kit (`useDraggable` for the current item, `useDroppable` on each placed item, "before it", and at the end of each tier), pointer and keyboard sensors, translated announcements. Keyboard alternative: "Place in {tier}" (end of the tier), then ←/→ to move it within its tier. Each action sends `PUT …/placements` and the returned room replaces the cached one (no optimistic update). |
|              | `components/GameAdminControls.tsx`                                                     | "Next item" with the reminder of the automatic setting, "Arrivals open" (`useUpdateRoomSettings({late_arrivals_allowed})`, US-2.10).                                                                                                                                                                                                                                                                                                                                                                            |
|              | `components/Countdown.tsx`, `components/PlacedList.tsx`, `components/GameItemView.tsx` | Countdown computed locally from the server end (`role="timer"`, not announced every second); "Placed n / m connected" with each status (placed, waiting, disconnected) and "(you)"; an item, large or small (image `alt` empty when the text is shown).                                                                                                                                                                                                                                                         |
| Real time    | `api/roomChannel.ts`                                                                   | `game.started` reads the room again (default behaviour); `participant.placed` adds the participant to `game.placed_participant_ids` in the cache.                                                                                                                                                                                                                                                                                                                                                               |
| Translations | `i18n/locales/fr.ts`, `en.ts`                                                          | `rooms.lobby.start.*`, `rooms.game.*`, `errors.api.{game_in_progress, no_placing_participant, not_a_placing_participant, item_not_current, round_not_in_progress}`.                                                                                                                                                                                                                                                                                                                                             |

### Tests

`backend/tests/integration/test_game_start.py` and `test_game_placements.py`, `test_game_rounds.py`, `test_game_reconnection.py`, `backend/tests/test_round_timers.py`; `frontend/src/api/roomChannel.test.ts` (`participant.placed`); `frontend/src/components/GameScreen.test.tsx`, `StartGameButton.test.tsx` and the game in progress in `pages/RoomPage.test.tsx`. All are described in the [testing guide](testing.md).

## 4. Known limitations

- The cooldown does not end yet: no timer at `cooldown_ends_at`, no "End now", no final placement (#96).
- Drag and drop with a pointer is not covered by the automated tests (jsdom has no layout): they place with the buttons.
- Final placements (cooldown) are not built: `phase = final` is ready in the table (#96).
- Closing a room during a game (#89) will have to close the game first (#98).
- "A game is in progress" lives in two places: `rooms.status = playing` and a `games` row not `closed`. The start writes both in one transaction, under the room lock; the closing (#98) must set the room back to `open` in the same transaction as the game.
