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
// par le room admin, le participant n'a plus de place : la page le lui dit.
const CLOSE_NOT_AUTHENTICATED: number = 4401;
const CLOSE_REMOVED: number = 4410;
const CLOSE_BANNED: number = 4411;
const NO_RETRY_CLOSE_CODES: ReadonlySet<number> = new Set([CLOSE_NOT_AUTHENTICATED, 4404]);
// Ouvertures ratées d'affilée (canal jamais ouvert : serveur injoignable, origine refusée…)
// avant d'abandonner et de prévenir l'utilisateur
const MAX_FAILED_OPENINGS: number = 5;
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

// Applique un événement à la salle en cache. La présence, un départ et « a placé » la modifient
// directement ; une arrivée ou des réglages la font relire. Une version qui ne suit pas la précédente veut dire qu'un
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
    // Qui a placé l'item en cours, jamais où (plateau privé)
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

// État du suivi en direct, pour la page
export interface RoomEventsState {
  // Le canal n'a pas pu s'ouvrir plusieurs fois d'affilée : plus de mise à jour en direct
  unavailable: boolean;
}

// Suit la salle en direct (docs/technical/realtime.md) : ouvre le canal, s'authentifie, répond au
// battement de cœur, applique les événements, se reconnecte, et ferme le canal au démontage. Les
// composants ne touchent jamais le socket. enabled : le lecteur a une place (salle chargée).
// onRemoved : le room admin vient de retirer le lecteur (banned : il l'a aussi banni) ; il doit
// garder la même identité d'un rendu à l'autre, sinon le canal serait rouvert.
export function useRoomEvents(
  code: string,
  viewer: RoomViewer | undefined,
  enabled: boolean,
  onRemoved: (banned: boolean) => void,
): RoomEventsState {
  const queryClient: QueryClient = useQueryClient();
  // Salle pour laquelle le suivi a été abandonné : en changer annule l'abandon
  const [abandonedRoom, setAbandonedRoom] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled || viewer === undefined) return undefined;
    const channelViewer: RoomViewer = viewer;
    const roomCode: string = canonicalRoomCode(code);
    let socket: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    let attempt: number = 0;
    let failedOpenings: number = 0;
    // Le nouvel essai après un 4401 n'a lieu qu'une fois tant qu'aucun message n'est arrivé
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
            // Sans session valable, la page le verra à sa prochaine requête
            if (refreshed && !stopped) connect();
          });
          return;
        }
        if (event.code === CLOSE_REMOVED || event.code === CLOSE_BANNED) {
          onRemoved(event.code === CLOSE_BANNED);
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
