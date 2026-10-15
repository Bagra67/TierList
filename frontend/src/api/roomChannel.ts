import { type QueryClient, useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';

import { canonicalRoomCode, roomQueryKey } from '../constants/rooms';
import { getAccessToken, refreshAccessToken } from './client';
import type { Room, RoomViewer } from './rooms';
import type { components } from './schema';

type RoomServerMessage = components['schemas']['RoomServerMessage'];
type RoomEvent = Exclude<RoomServerMessage, components['schemas']['PingMessage']>;
type RoomClientMessage = components['schemas']['RoomClientMessage'];

// Codes de fermeture après lesquels se reconnecter ne servirait à rien : pas de session valable,
// ou pas de place dans la salle (backend : app/constants/rooms.py)
const NO_RETRY_CLOSE_CODES: ReadonlySet<number> = new Set([4401, 4404]);
// Attente avant de se reconnecter : de 0,5 s, doublée à chaque échec, jusqu'à 10 s
const RECONNECT_MIN_DELAY_MS: number = 500;
const RECONNECT_MAX_DELAY_MS: number = 10_000;
// Fermeture voulue par la page (démontage)
const NORMAL_CLOSURE: number = 1000;

// Canal de la salle, sur la même origine que la page (le proxy /api le transmet au backend)
function roomChannelUrl(code: string): string {
  const protocol: string = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/api/rooms/${encodeURIComponent(code)}/ws`;
}

// Backoff exponentiel avec gigue : des clients coupés ensemble ne reviennent pas tous à l'instant
function reconnectDelay(attempt: number): number {
  const ceiling: number = Math.min(RECONNECT_MAX_DELAY_MS, RECONNECT_MIN_DELAY_MS * 2 ** attempt);
  return ceiling / 2 + Math.random() * (ceiling / 2);
}

// Un compte s'authentifie par son access token (jamais dans l'URL) ; un invité, par son cookie
async function channelAccessToken(viewer: RoomViewer): Promise<string | null> {
  if (viewer !== 'account') return null;
  if (getAccessToken() === null) await refreshAccessToken();
  return getAccessToken();
}

// Applique un événement à la salle en cache. La présence la modifie directement ; une arrivée ou
// des réglages la font relire. Une version qui ne suit pas la précédente veut dire qu'un
// événement a été manqué : la salle est relue (le serveur ne rejoue jamais le passé).
function applyRoomEvent(queryClient: QueryClient, roomCode: string, event: RoomEvent): void {
  const queryKey = roomQueryKey(roomCode);
  const room: Room | undefined = queryClient.getQueryData<Room>(queryKey);
  if (room !== undefined && event.room_version <= room.version) return; // déjà dans la salle lue
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
  void queryClient.invalidateQueries({ queryKey });
}

// Suit la salle en direct (docs/technical/realtime.md) : ouvre le canal, s'authentifie, répond au
// battement de cœur, applique les événements, se reconnecte, et ferme le canal au démontage. Les
// composants ne touchent jamais le socket. enabled : le lecteur a une place (salle chargée).
export function useRoomEvents(
  code: string,
  viewer: RoomViewer | undefined,
  enabled: boolean,
): void {
  const queryClient: QueryClient = useQueryClient();

  useEffect(() => {
    if (!enabled || viewer === undefined) return undefined;
    const channelViewer: RoomViewer = viewer;
    const roomCode: string = canonicalRoomCode(code);
    let socket: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    let attempt: number = 0;
    let stopped: boolean = false;

    function send(target: WebSocket, message: RoomClientMessage): void {
      target.send(JSON.stringify(message));
    }

    function connect(): void {
      const current: WebSocket = new WebSocket(roomChannelUrl(roomCode));
      socket = current;
      current.addEventListener('open', () => {
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
        if (message.type === 'ping') {
          send(current, { type: 'pong' });
          return;
        }
        applyRoomEvent(queryClient, roomCode, message);
      });
      current.addEventListener('close', (event: CloseEvent) => {
        if (stopped || NO_RETRY_CLOSE_CODES.has(event.code)) return;
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
  }, [code, viewer, enabled, queryClient]);
}
