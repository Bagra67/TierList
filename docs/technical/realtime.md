# Real time

English | [Français](realtime.fr.md)

How rooms push rounds, placements, presence and timers to every participant: transport, message format, authentication of the socket, reconnection, server-side timers and scaling. Decided in spike #74, **built in #85** (§3) for the room channel and the presence; rounds, placements and timers come with the game issues. To understand, debug or extend the channel, start with the [WebSocket guide](websocket.md). What a room is for the user: [game flow](../product/milestone-1/game-flow.md) and [lifecycles](../product/milestone-1/lifecycles.md).

## 1. Functional overview

### What must reach the participants

A room has **at most 10 participants** (room admin included) and a game **at most 32 rounds**. Every participant must see, without reloading the page:

| Moment                                            | Event pushed to the room                                                      |
| ------------------------------------------------- | ----------------------------------------------------------------------------- |
| Someone joins, leaves, connects or disconnects    | The lobby / participant list changes (`3 participants out of 10`)             |
| The admin edits the settings or locks arrivals    | The new settings, "arrivals open / locked"                                    |
| The admin starts the game                         | The game starts with its first round                                          |
| A round starts                                    | `Item n out of N`, and its end time when the room uses a timer                |
| A participant places or moves the current item    | **Who** has placed, never **where** (rankings stay private until the results) |
| A round ends (admin "next", timer, everyone done) | The round is over; absent placements are recorded by the server               |
| The last round ends                               | The cooldown starts, with its end time                                        |
| The cooldown ends (timer or admin "End now")      | The game is closed: results available, room back to _Open_                    |
| The admin closes the room, or it is inactive      | The room is closed; every participant leaves                                  |

Timers: the per-item **round timer** (room setting), the **cooldown** (room setting), the **room inactivity delay** (application setting). A **disconnected** participant keeps their seat and ranking, gets absent placements for the rounds that end meanwhile, and is not waited for by "everyone done".

### Rules

- The **server is the only authority**: it decides when a round ends, records the placements and runs the timers. A client only displays.
- A participant may open several tabs: they are **connected** as long as one of them is.
- A participant who comes back (reload, network drop, other device) finds the current state: the current round, their own placements, the time left.

### Not available yet

The game events (rounds, placements, cooldown) and the server-side timers (§2.8) come with the game issues (#91 and next). Holograms, public rooms and chat (later milestones) will reuse the same channel.

## 2. Technical design

### 2.1 Options considered

| Option                                      | For                                                                                                             | Against                                                                                                                       |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Polling (`GET` every few seconds)           | Nothing new                                                                                                     | Late (a round may last a few seconds), many useless requests, no presence                                                     |
| Server-Sent Events + REST commands          | Plain HTTP, built-in reconnection                                                                               | Max 6 HTTP/1.1 connections per domain (several tabs), `EventSource` cannot send the `Authorization` header, presence is vague |
| WebSocket, everything on the socket         | One channel, fewest requests                                                                                    | Validation, error codes, authorization and tests must be rebuilt outside OpenAPI and the existing services                    |
| **WebSocket push + REST commands** (chosen) | Commands keep OpenAPI, Pydantic validation, `ErrorCode`, services and tests; the socket gives push and presence | Two channels to coordinate (handled by the resynchronisation of §2.6)                                                         |

**Decision**: a WebSocket per tab, used **only to push** events from the server and to know who is connected. Every **action** (join, place, next, start, close, settings) stays a REST route, like the rest of the API.

### 2.2 Transport

- One endpoint per room: `WS /rooms/{room_code}/ws` (FastAPI `WebSocket`), reached as `/api/rooms/{room_code}/ws` through the Vite proxy, which then needs `ws: true` in `frontend/vite.config.ts`.
- **Server → client**: the events of §2.3. **Client → server**: only the authentication message (§2.4) and the heartbeat reply; any other message closes the socket.
- A command is a normal REST call: the route calls the service, the service commits, **then** publishes the event to the room (§2.8). The participant who sent the command gets the HTTP response; everyone (sender included) gets the event.
- No new dependency: `fastapi[standard]` already ships uvicorn with `websockets`, `uvloop` and `httptools` (present in `backend/uv.lock`).

### 2.3 Message format

Every message is a JSON object with the same envelope:

```json
{
  "type": "round.started",
  "room_version": 12,
  "data": {
    "round_number": 3,
    "round_count": 20,
    "tile_id": "…",
    "ends_at": "2026-10-10T18:30:12Z"
  }
}
```

- `type`: lowercase, dotted `subject.event` (`participant.joined`, `participant.placed`, `round.started`, `round.ended`, `cooldown.started`, `game.closed`, `room.closed`…).
- `room_version`: an integer incremented by the server at each change of the room, in the same transaction. A client that receives a version that is not "previous + 1" knows it missed something and resynchronises (§2.6).
- `data`: the payload of the event, never the position of another participant's placements.
- Each event is a Pydantic model; the union of all of them is a **discriminated union on `type`**. These models are added to the components of the OpenAPI schema (extra schemas in the custom `openapi()`), so that `pnpm gen:api` generates their TypeScript types like the REST ones (AGENTS.md §23: API types are never written by hand).
- Errors: the server closes the socket with an application close code (`4000`–`4999`) and the `ErrorCode` as reason (e.g. `4401` + `not_authenticated`, `4403` + `room_access_denied`, `4404` + `room_not_found`). The frontend translates the code like any API error (AGENTS.md §50). Exact codes are created with the rooms.

### 2.4 Authentication of the socket

A browser cannot send the `Authorization` header when it opens a WebSocket, and the refresh cookie (`Path=/api/auth`) never reaches `/api/rooms`. Hence:

- **Account**: the socket opens unauthenticated; the first client message must be `{"type": "auth", "access_token": "…"}` within a few seconds, otherwise the server closes it. The server checks it with the existing `AuthService.authenticate_access_token`. The token is **never put in the URL**, which would end up in proxy and server logs. When the frontend refreshes the access token (single-flight refresh of `frontend/src/api/client.ts`), it does not need to reopen the socket: the token is only checked at connection.
- **Guest**: the guest is recognised by an `HttpOnly` cookie scoped to `/api/rooms`, which the browser sends automatically with the handshake (same origin). The token, its cookie (`guest_token`, `Path=/api/rooms/<code>`) and its lifetime are described in the [rooms guide](rooms.md#24-guests).
- **Origin check**: since a cookie authenticates guests, the handshake is refused when its `Origin` header is not the application's origin (protection against cross-site WebSocket hijacking).
- **Authorization**: once authenticated, the server checks that the account or guest **holds a seat in this room** before registering the socket. Nothing is pushed before that.

### 2.5 Presence and heartbeat

- The server sends a heartbeat (`{"type": "ping"}`) at a fixed interval; the client answers `{"type": "pong"}`. A socket without answer is closed. The interval also keeps the socket alive behind proxies that close idle connections.
- A participant becomes **disconnected** when their last socket has been closed for longer than a **grace delay**, so that a page reload or a short network drop does not count as a disconnection (and does not trigger "everyone done" on their behalf). Interval and grace delay are `Settings` values whose defaults are chosen at implementation.
- `connected` is stored on the participant row and written only when it changes (connection, end of grace delay), not at each heartbeat.

### 2.6 Reconnection and resynchronisation

- The client reconnects automatically with an **exponential backoff with jitter** (for example from 0.5 s up to 10 s), except after a close code meaning "do not retry" (room closed, access denied).
- After **every** (re)connection, and whenever a `room_version` gap is seen, the client **refetches the room snapshot** with the REST `GET` (TanStack Query `invalidateQueries`). The server therefore never replays past events: the snapshot is the truth, the events only keep it up to date between two snapshots.

### 2.7 Frontend: events and TanStack Query

```
REST GET /rooms/{code} ──▶ TanStack Query cache ──▶ components
WS events ──▶ useRoomEvents(roomCode) ──┘ (setQueryData / invalidateQueries)
```

- The room state stays a **TanStack Query** query fed by the REST snapshot; the commands stay mutations of the API layer (`frontend/src/api/`).
- One hook, `useRoomEvents(roomCode)` in `frontend/src/api/`, owns the socket: opening, authentication, heartbeat, reconnection, closing on unmount. Components never touch the socket.
- Small events update the cache directly (`queryClient.setQueryData`: someone placed, presence); larger ones invalidate the query (`invalidateQueries`: new round, results), which refetches the snapshot.
- Countdowns are computed locally from the `ends_at` sent by the server.

### 2.8 Server-side timers

- The server is the only clock. A round with a timer and the cooldown store their **end time** (`ends_at`, UTC) in the database; the events send it, the clients display the countdown from it.
- In the process, an `asyncio` task waits for each deadline and calls the service transition; it is cancelled when the round ends earlier (admin "next", everyone done). At startup, the pending deadlines are read from the database and re-scheduled: a restart loses no timer.
- **Races** (timer, "next" and "everyone done" at the same time): each transition runs in a transaction that locks the room row and checks the expected state (the round is still in progress); the second one finds the round already ended and does nothing. Transitions are therefore **idempotent**.
- The **inactivity delay** of a room is handled by a periodic sweep that closes the rooms inactive for too long.
- SQLAlchemy is synchronous: from async code (the socket, the timers), the database calls go through the threadpool (`run_in_threadpool`) and never block the event loop.

### 2.9 Scaling

**Why a room is cheap**: at most 10 sockets and a few small events per round. The load is the number of concurrent rooms × 10 sockets, plus the REST commands that hit the database. Bottlenecks expected, in order: database access (synchronous SQLAlchemy through the threadpool, pool size), then the event loop of one process, then the network. No capacity figure is promised: it is **measured by a load test** before public rooms (tool chosen and justified then, AGENTS.md §27).

The path is in stages; each stage is taken when the metrics of the previous one require it.

**Stage 0: milestone 1 (what gets built).** One process, one worker. An in-memory `ConnectionRegistry` (room → open sockets of this process), `asyncio` timers, events published in the process. A restart closes every socket: the clients reconnect and refetch their snapshot, the timers are re-scheduled from the database.

**Stage 1: bigger machine (configuration only).** More CPU and memory, database pool and threadpool sizes tuned through `Settings`, `uvloop` and `httptools` (already installed). What to watch: open sockets per process, event loop lag, waiting time for a database connection, delay between publication and delivery.

**Stage 2: several instances or workers.** Three problems appear:

| Problem                                                       | Answer                                                                                                                                                                                                                                                                                      |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Fan-out**: the sockets of a room are on different instances | A **broker**: each instance listens to channel `room:{id}` for the rooms it holds sockets for; the services publish there. First choice **PostgreSQL `LISTEN/NOTIFY`**: no new service, payload ≤ 8 kB (events are small), one listening connection per instance.                           |
| **Timers** must fire only once                                | The deadlines are already in the database: every instance runs a short periodic sweep `SELECT … WHERE ends_at <= now() FOR UPDATE SKIP LOCKED` (or a PostgreSQL advisory lock per room) instead of in-process tasks. A double fire would be harmless anyway (idempotent transitions, §2.8). |
| **Presence** across instances                                 | `connected` is already in the database; a participant stays connected while at least one socket exists on any instance (a counter per participant, or a Redis key with expiry at stage 3).                                                                                                  |

An alternative without a broker is **sticky routing per room**: the load balancer sends the socket **and** the REST commands of a room to the same instance (consistent hash on `room_code`, e.g. Nginx or HAProxy `hash … consistent`). Everything stays in memory, but adding or removing an instance moves rooms (their clients reconnect and resynchronise).

In both cases the load balancer must accept the WebSocket upgrade, with an idle timeout longer than the heartbeat interval, and a deployment closes the sockets with code `1012` (service restart) so that clients reconnect to another instance.

**Stage 3: high volume (public rooms, holograms).** `LISTEN/NOTIFY` is replaced by **Redis pub/sub** (Redis Streams if replaying events becomes necessary), presence moves to Redis keys with expiry, and the WebSocket processes can be separated from the REST processes (same code, scaled independently). Redis is a new dependency, justified at that time.

**What the code respects from milestone 1**, so that stages 1 to 3 only replace one component:

- The services publish through one small `RoomEventPublisher` (`publish(room_id, event)`), with an in-memory implementation; they never touch a socket. It is the only abstraction introduced in advance, because it is the seam stage 2 needs (AGENTS.md §47).
- Publication happens **after the commit**. If the process stops between the two, the `room_version` gap and the resynchronisation of §2.6 repair it: no outbox table at this scale.
- The database is the truth (state, `ends_at`, `connected`, `room_version`); the process keeps no room state in memory other than its open sockets.
- Timers call the same idempotent service transitions as the REST commands.
- The REST routes stay stateless: any instance can serve them.

### 2.10 Known limitations

- **One worker** in milestone 1: starting the backend with several workers would split the rooms (stage 2 needed first).
- The access token is checked only when the socket opens: a session revoked during a game keeps receiving the events of that room until the socket closes (the commands, on REST, are refused at once). Acceptable since the socket carries nothing private beyond the room.
- The inactivity delay (automatic closing of a room, #90) is still to be chosen.
- A guest socket already open stays open when the guest seat expires, until it closes (like a revoked session).
- The channel only accepts the origin of `FRONTEND_BASE_URL`: opening the app through another address (e.g. `http://127.0.0.1:5173` instead of `http://localhost:5173`) has its channel refused.
- What happens when the **room admin** disconnects (nobody can click "next" or close) is a product question not covered by the [lifecycles](../product/milestone-1/lifecycles.md); the timers still make the game move on.

## 3. In the code

Built in #85. What exists today:

- **Events** (`app/schemas/room_events.py`), a discriminated union on `type`, all carrying `room_version`:

  | `type`                  | `data`                        | Sent when                                                                             | Frontend                |
  | ----------------------- | ----------------------------- | ------------------------------------------------------------------------------------- | ----------------------- |
  | `participant.joined`    | `{participant_id}`            | An account or a guest joins (`POST /join`, `POST /guests`)                            | Reads the room again    |
  | `participant.presence`  | `{participant_id, connected}` | First socket of a participant opened; last one closed for longer than the grace delay | Updates the cached room |
  | `room.settings_updated` | `{}`                          | The room admin changes a setting (an empty change sends nothing)                      | Reads the room again    |

  Channel messages: `{"type": "ping"}` from the server, `{"type": "pong"}` and `{"type": "auth", "access_token": …}` from the client. `RoomServerMessage` and `RoomClientMessage` are added to the OpenAPI components (`_openapi_with_room_messages` in `app/main.py`).

- **Room version**: `rooms.version`, incremented by `RoomService` in the same transaction as the change (join, guest join, settings, presence), returned as `version` by the room API.
- **Authentication**: the first message is always `auth`, within `ROOM_AUTH_TIMEOUT_SECONDS`: an account sends its access token, a guest sends `null` and is recognised by its `guest_token` cookie (`Path=/api/rooms/<code>`, [rooms guide](rooms.md#24-guests)). An account comes first, like in REST.
- **Close codes** (`app/constants/rooms.py`), with the `ErrorCode` as reason; the client does not reconnect after `4401` and `4404`:

  | Code       | Reason              | When                                                                             |
  | ---------- | ------------------- | -------------------------------------------------------------------------------- |
  | HTTP `403` | —                   | `Origin` is not the origin of `FRONTEND_BASE_URL` (refused before the handshake) |
  | `4400`     | `invalid_message`   | A message that is not `auth` first, then not `pong`                              |
  | `4401`     | `not_authenticated` | No `auth` in time, invalid token, or neither token nor guest cookie              |
  | `4404`     | `room_not_found`    | Unknown room, or the reader has no seat in it                                    |
  | `4408`     | `heartbeat_timeout` | No `pong` within `ROOM_HEARTBEAT_TIMEOUT_SECONDS` after a ping                   |

- **Settings** (`app/core/config.py`, `.env.example`):

  | Variable                          | Purpose                                                                                               | Default |
  | --------------------------------- | ----------------------------------------------------------------------------------------------------- | ------- |
  | `ROOM_HEARTBEAT_INTERVAL_SECONDS` | Ping after this silence of the client                                                                 | `10`    |
  | `ROOM_HEARTBEAT_TIMEOUT_SECONDS`  | Socket closed without `pong` within this delay                                                        | `5`     |
  | `ROOM_PRESENCE_GRACE_SECONDS`     | A participant becomes disconnected this long after their last socket closed (a reload does not blink) | `3`     |
  | `ROOM_AUTH_TIMEOUT_SECONDS`       | Delay of the `auth` message                                                                           | `5`     |

- **Startup**: the lifespan (`app/main.py`) sets every participant back to disconnected, since a starting process has no open socket.
- **Robustness**:
  - an account whose channel is refused with `4401` retries **once** with a refreshed access token (the token lasts 15 minutes; a lobby left open longer would otherwise freeze at its next reconnection); a second `4401` in a row stops it;
  - after 5 openings in a row that never opened (server unreachable, origin refused, which the browser reports as `1006`), the hook stops and the lobby says live updates are unavailable;
  - a binary frame from the client closes the channel with `4400` `invalid_message`;
  - a participant who comes back while their departure is being written is set connected again (`schedule_disconnect`: the cancellation cannot stop the thread that writes).
- **Event order**: each publication is broadcast by its own task, so two events published at the same time may reach a socket in the wrong order. The client then sees a version gap and reads the room again: the result stays right, at the cost of one request.

| Layer        | File                                             | Content                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------------ | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Route        | `api/routes/room_channel.py`                     | `WS /rooms/{code}/ws`: origin check, `_receive_auth`, `_find_seat` (in the threadpool), `_serve` (presence), `_heartbeat`.                                                                                                                                                                                                                                                                                          |
| Registry     | `services/room_channel.py`                       | `RoomEventPublisher` (protocol) and `ConnectionRegistry` (`room_connections`): open sockets per room and their participant, `publish` handed over from the REST threadpool to the event loop (`call_soon_threadsafe`), pending disconnections (`schedule_disconnect`, `cancel_pending_disconnect`).                                                                                                                 |
| Service      | `services/rooms.py`                              | Publishes after the commit (`_publish_joined`, settings); `seat_of`, `set_presence` (writes and publishes only on change), `reset_presence`.                                                                                                                                                                                                                                                                        |
| Dependencies | `api/dependencies.py`                            | `get_room_event_publisher`, `get_session_factory` (short sessions for the channel, replaced in the tests). `get_connection_registry` (the registry, injected into the route).                                                                                                                                                                                                                                       |
| Frontend     | `api/roomChannel.ts`                             | `useRoomEvents(code, viewer, enabled)`: opens `/api/rooms/<CODE>/ws`, sends `auth` (`getAccessToken`, refreshed if missing), answers `pong`, applies the events, reads the room again after each (re)connection and after a version gap, reconnects with exponential backoff and jitter (0.5 s to 10 s). One retry with a refreshed token after `4401`; gives up after 5 failed openings and returns `unavailable`. |
| Frontend     | `components/RoomLobby.tsx`, `pages/RoomPage.tsx` | Presence dot (filled online, hollow offline) with an `online` / `offline` text for screen readers; the hook is active once the room is loaded.                                                                                                                                                                                                                                                                      |
| Dev          | `frontend/vite.config.ts`                        | `ws: true` on the `/api` proxy.                                                                                                                                                                                                                                                                                                                                                                                     |

Tests: `backend/tests/integration/test_room_channel.py`, the publication tests of `test_rooms.py` / `test_room_guests.py`, `backend/tests/test_room_connections.py` (registry), `frontend/src/api/roomChannel.test.ts` (fake `WebSocket`, `src/test/fakeWebSocket.ts`), described in the [testing guide](testing.md).
