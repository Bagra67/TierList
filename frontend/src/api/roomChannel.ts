import { type QueryClient, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

import { canonicalRoomCode, roomQueryKey } from '../constants/rooms';
import { getAccessToken, refreshAccessToken } from './client';
import type { Room, RoomViewer } from './rooms';
import type { components } from './schema';

type RoomServerMessage = components['schemas']['RoomServerMessage'];
type RoomEvent = Exclude<RoomServerMessage, components['schemas']['PingMessage']>;
type RoomClientMessage = components['schemas']['RoomClientMessage'];

const CLOSE_NOT_AUTHENTICATED: number = 4401;
const CLOSE_ROOM_NOT_FOUND: number = 4404;
const CLOSE_REMOVED: number = 4410;
const CLOSE_BANNED: number = 4411;
const CLOSE_ROOM_CLOSED: number = 4412;
export type RemovalReason = 'removed' | 'banned' | 'closed';
const REMOVAL_REASONS: ReadonlyMap<number, RemovalReason> = new Map([
  [CLOSE_REMOVED, 'removed'],
  [CLOSE_BANNED, 'banned'],
  [CLOSE_ROOM_CLOSED, 'closed'],
]);
const NO_RETRY_CLOSE_CODES: ReadonlySet<number> = new Set([
  CLOSE_NOT_AUTHENTICATED,
  CLOSE_ROOM_NOT_FOUND,
]);
const MAX_FAILED_OPENINGS: number = 5;
const RECONNECT_MIN_DELAY_MS: number = 500;
const RECONNECT_MAX_DELAY_MS: number = 10_000;
const NORMAL_CLOSURE: number = 1000;

function roomChannelUrl(code: string): string {
  const protocol: string = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/api/rooms/${encodeURIComponent(code)}/ws`;
}

function exponentialBackoffWithJitterMs(attempt: number): number {
  const ceiling: number = Math.min(RECONNECT_MAX_DELAY_MS, RECONNECT_MIN_DELAY_MS * 2 ** attempt);
  const jitter: number = Math.random() * (ceiling / 2);
  return ceiling / 2 + jitter;
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

export function useRoomEvents(
  code: string,
  viewer: RoomViewer | undefined,
  viewerHasSeat: boolean,
  stableOnRemoved: (reason: RemovalReason) => void,
): RoomEventsState {
  const queryClient: QueryClient = useQueryClient();
  const [abandonedRoom, setAbandonedRoom] = useState<string | null>(null);

  useEffect(() => {
    if (!viewerHasSeat || viewer === undefined) return undefined;
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

    function readRoomAgainAfterMissedEvents(): void {
      void queryClient.invalidateQueries({ queryKey: roomQueryKey(roomCode) });
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
          readRoomAgainAfterMissedEvents();
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
          stableOnRemoved(removalReason);
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
        retryTimer = setTimeout(connect, exponentialBackoffWithJitterMs(attempt));
        attempt += 1;
      });
    }

    connect();
    return () => {
      stopped = true;
      clearTimeout(retryTimer);
      socket?.close(NORMAL_CLOSURE);
    };
  }, [code, viewer, viewerHasSeat, stableOnRemoved, queryClient]);

  return { unavailable: viewerHasSeat && abandonedRoom === canonicalRoomCode(code) };
}
