import { type QueryClient, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

import { canonicalRoomCode, roomQueryKey } from '../constants/rooms';
import { getAccessToken, refreshAccessToken } from './client';
import type { Room, RoomViewer } from './rooms';
import type { components } from './schema';

type RoomServerMessage = components['schemas']['RoomServerMessage'];
type RoomEvent = Exclude<RoomServerMessage, components['schemas']['PingMessage']>;
type RoomClientMessage = components['schemas']['RoomClientMessage'];

// Codes de fermeture du serveur (backend : app/constants/rooms.py). Après NOT_AUTHENTICATED, un
// compte retente une fois avec un token rafraîchi (le sien a pu expirer pendant que le lobby était
// ouvert) ; sinon, comme après ROOM_NOT_FOUND, se reconnecter ne servirait à rien. Retiré ou banni
// par le room admin, ou salle fermée, le participant n'a plus de place : la page le lui dit.
const CLOSE_NOT_AUTHENTICATED: number = 4401;
const CLOSE_REMOVED: number = 4410;
const CLOSE_BANNED: number = 4411;
const CLOSE_ROOM_CLOSED: number = 4412;
export type RemovalReason = 'removed' | 'banned' | 'closed';
const REMOVAL_REASONS: ReadonlyMap<number, RemovalReason> = new Map([
  [CLOSE_REMOVED, 'removed'],
  [CLOSE_BANNED, 'banned'],
  [CLOSE_ROOM_CLOSED, 'closed'],
]);
const NO_RETRY_CLOSE_CODES: ReadonlySet<number> = new Set([CLOSE_NOT_AUTHENTICATED, 4404]);
const MAX_FAILED_OPENINGS: number = 5;
const RECONNECT_MIN_DELAY_MS: number = 500;
const RECONNECT_MAX_DELAY_MS: number = 10_000;
const NORMAL_CLOSURE: number = 1000;

function roomChannelUrl(code: string): string {
  const protocol: string = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/api/rooms/${encodeURIComponent(code)}/ws`;
}

// Backoff exponentiel avec gigue : des clients coupés ensemble ne reviennent pas tous à l'instant
function reconnectDelay(attempt: number): number {
  const ceiling: number = Math.min(RECONNECT_MAX_DELAY_MS, RECONNECT_MIN_DELAY_MS * 2 ** attempt);
  return ceiling / 2 + Math.random() * (ceiling / 2);
}

async function channelAccessToken(viewer: RoomViewer): Promise<string | null> {
  if (viewer !== 'account') return null;
  if (getAccessToken() === null) await refreshAccessToken();
  return getAccessToken();
}

function applyRoomEvent(queryClient: QueryClient, roomCode: string, event: RoomEvent): void {
  const queryKey = roomQueryKey(roomCode);
  const room: Room | undefined = queryClient.getQueryData<Room>(queryKey);
  if (room !== undefined && event.room_version <= room.version) return;
  if (room === undefined || event.room_version !== room.version + 1) {
    void queryClient.invalidateQueries({ queryKey });
    return;
  }
  if (event.type === 'participant.presence') {
    queryClient.setQueryData<Room>(queryKey, {
      ...room,
      version: event.room_version,
      participants: room.participants.map((participant) =>
        participant.id === event.data.participant_id
          ? { ...participant, connected: event.data.connected }
          : participant,
      ),
    });
    return;
  }
  if (event.type === 'participant.removed') {
    queryClient.setQueryData<Room>(queryKey, {
      ...room,
      version: event.room_version,
      participants: room.participants.filter(
        (participant) => participant.id !== event.data.participant_id,
      ),
    });
    return;
  }
  if (event.type === 'participant.placed' && room.game !== null) {
    queryClient.setQueryData<Room>(queryKey, {
      ...room,
      version: event.room_version,
      game: {
        ...room.game,
        placed_participant_ids: [...room.game.placed_participant_ids, event.data.participant_id],
      },
    });
    return;
  }
  void queryClient.invalidateQueries({ queryKey });
}

export interface RoomEventsState {
  unavailable: boolean;
}

// Suit la salle en direct (docs/technical/realtime.md) : ouvre le canal, s'authentifie, répond au
// battement de cœur, applique les événements, se reconnecte, et ferme le canal au démontage. Les
// composants ne touchent jamais le socket. enabled : le lecteur a une place (salle chargée).
// onRemoved : le lecteur n'a plus de place (retiré, banni, ou salle fermée) ; il doit garder la
// même identité d'un rendu à l'autre, sinon le canal serait rouvert.
export function useRoomEvents(
  code: string,
  viewer: RoomViewer | undefined,
  enabled: boolean,
  onRemoved: (reason: RemovalReason) => void,
): RoomEventsState {
  const queryClient: QueryClient = useQueryClient();
  const [abandonedRoom, setAbandonedRoom] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled || viewer === undefined) return undefined;
    const channelViewer: RoomViewer = viewer;
    const roomCode: string = canonicalRoomCode(code);
    let socket: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    let attempt: number = 0;
    let failedOpenings: number = 0;
    let retriedWithFreshToken: boolean = false;
    let stopped: boolean = false;

    function send(target: WebSocket, message: RoomClientMessage): void {
      target.send(JSON.stringify(message));
    }

    function connect(): void {
      const current: WebSocket = new WebSocket(roomChannelUrl(roomCode));
      socket = current;
      let opened: boolean = false;
      current.addEventListener('open', () => {
        opened = true;
        failedOpenings = 0;
        void channelAccessToken(channelViewer).then((accessToken: string | null) => {
          if (stopped || current.readyState !== WebSocket.OPEN) return;
          send(current, { type: 'auth', access_token: accessToken });
          // Ce qui a changé pendant la coupure n'est pas rejoué : la salle est relue
          void queryClient.invalidateQueries({ queryKey: roomQueryKey(roomCode) });
        });
      });
      current.addEventListener('message', (event: MessageEvent<string>) => {
        const message: RoomServerMessage = JSON.parse(event.data) as RoomServerMessage;
        attempt = 0;
        retriedWithFreshToken = false;
        if (message.type === 'ping') {
          send(current, { type: 'pong' });
          return;
        }
        applyRoomEvent(queryClient, roomCode, message);
      });
      current.addEventListener('close', (event: CloseEvent) => {
        if (stopped) return;
        if (
          event.code === CLOSE_NOT_AUTHENTICATED &&
          channelViewer === 'account' &&
          !retriedWithFreshToken
        ) {
          retriedWithFreshToken = true;
          void refreshAccessToken().then((refreshed: boolean) => {
            if (refreshed && !stopped) connect();
          });
          return;
        }
        const removalReason: RemovalReason | undefined = REMOVAL_REASONS.get(event.code);
        if (removalReason !== undefined) {
          onRemoved(removalReason);
          return;
        }
        if (NO_RETRY_CLOSE_CODES.has(event.code)) return;
        if (!opened) {
          failedOpenings += 1;
          if (failedOpenings >= MAX_FAILED_OPENINGS) {
            setAbandonedRoom(roomCode);
            return;
          }
        }
        retryTimer = setTimeout(connect, reconnectDelay(attempt));
        attempt += 1;
      });
    }

    connect();
    return () => {
      stopped = true;
      clearTimeout(retryTimer);
      socket?.close(NORMAL_CLOSURE);
    };
  }, [code, viewer, enabled, onRemoved, queryClient]);

  return { unavailable: enabled && abandonedRoom === canonicalRoomCode(code) };
}
