import {
  type QueryClient,
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';

import { canonicalRoomCode, roomQueryKey } from '../constants/rooms';
import { ApiError } from '../errors/apiError';
import { apiClient, dataOrThrow } from './client';
import type { components } from './schema';

export type Room = components['schemas']['RoomResponse'];
export type Participant = components['schemas']['ParticipantResponse'];
export type RoomBan = components['schemas']['RoomBanResponse'];
// Salle rejointe en invité, avec son lien perso (donné une seule fois)
export type GuestRoom = components['schemas']['GuestRoomResponse'];
export type RoomSettings = components['schemas']['RoomSettingsResponse'];
export type ItemOrder = components['schemas']['ItemOrder'];
export type AutoAdvance = components['schemas']['AutoAdvance'];
type CreateRoomRequest = components['schemas']['CreateRoomRequest'];
type JoinAsGuestRequest = components['schemas']['JoinAsGuestRequest'];
// Réglages à changer : ceux qui sont absents restent tels quels
export type RoomSettingsChanges = components['schemas']['UpdateRoomSettingsRequest'];

async function createRoom(body: CreateRoomRequest): Promise<Room> {
  return dataOrThrow(await apiClient.POST('/rooms', { body }));
}

async function getRoom(code: string, signal?: AbortSignal): Promise<Room> {
  return dataOrThrow(await apiClient.GET('/rooms/{code}', { params: { path: { code } }, signal }));
}

async function joinRoom(code: string, signal?: AbortSignal): Promise<Room> {
  return dataOrThrow(
    await apiClient.POST('/rooms/{code}/join', { params: { path: { code } }, signal }),
  );
}

async function joinAsGuest(code: string, body: JoinAsGuestRequest): Promise<GuestRoom> {
  return dataOrThrow(
    await apiClient.POST('/rooms/{code}/guests', { params: { path: { code } }, body }),
  );
}

// Lien perso ouvert (US-5.4) : le backend pose le cookie de l'invité sur ce navigateur
async function restoreGuestSession(
  code: string,
  token: string,
  signal?: AbortSignal,
): Promise<GuestRoom> {
  return dataOrThrow(
    await apiClient.POST('/rooms/{code}/guest-session', {
      params: { path: { code } },
      body: { token },
      signal,
    }),
  );
}

// Invité qui a perdu son lien perso : un nouveau jeton remplace l'ancien (cookie compris)
async function renewGuestLink(code: string): Promise<GuestRoom> {
  return dataOrThrow(
    await apiClient.POST('/rooms/{code}/guest-link', { params: { path: { code } } }),
  );
}

// Ouvrir une salle avec son compte, c'est y entrer (US-2.4) : sans place (404), l'utilisateur la
// rejoint comme joueur. Rejoindre est idempotent : une relecture ne crée pas de seconde place, et
// un mauvais code donne toujours room_not_found.
async function enterRoom(code: string, signal?: AbortSignal): Promise<Room> {
  try {
    return await getRoom(code, signal);
  } catch (error) {
    if (error instanceof ApiError && error.code === 'room_not_found') {
      return joinRoom(code, signal);
    }
    throw error;
  }
}

async function updateRoomSettings(code: string, changes: RoomSettingsChanges): Promise<Room> {
  return dataOrThrow(
    await apiClient.PATCH('/rooms/{code}/settings', {
      params: { path: { code } },
      body: changes,
    }),
  );
}

// Supprime la place d'un participant (US-2.11) ; avec ban, il ne peut plus revenir (US-2.12)
async function removeParticipant(code: string, participantId: string, ban: boolean): Promise<Room> {
  return dataOrThrow(
    await apiClient.DELETE('/rooms/{code}/participants/{participant_id}', {
      params: { path: { code, participant_id: participantId }, query: { ban } },
    }),
  );
}

async function unban(code: string, banId: string): Promise<Room> {
  return dataOrThrow(
    await apiClient.DELETE('/rooms/{code}/bans/{ban_id}', {
      params: { path: { code, ban_id: banId } },
    }),
  );
}

// La salle renvoyée par une création ou une modification remplace celle du cache : le lobby
// l'affiche sans nouvelle lecture
function storeRoom(queryClient: QueryClient, room: Room): void {
  queryClient.setQueryData(roomQueryKey(room.code), room);
}

// Qui ouvre la salle : un compte connecté, ou un visiteur sans compte (invité, peut-être déjà
// reconnu par son cookie)
export type RoomViewer = 'account' | 'guest';

// Une erreur 4xx ne change pas en réessayant (salle introuvable, lien perso expiré…)
function shouldRetry(failureCount: number, error: Error): boolean {
  return !(error instanceof ApiError && error.status < 500) && failureCount < 1;
}

// Salle ouverte par ce lecteur, lu une fois la session connue (viewer undefined : en attente).
// Un compte y entre (enterRoom) ; un invité la lit grâce à son cookie, ou d'abord grâce au jeton
// de son lien perso (guestToken), qui pose ce cookie.
export function useRoom(
  code: string,
  viewer: RoomViewer | undefined,
  guestToken: string | null = null,
): UseQueryResult<Room> {
  const roomCode: string = canonicalRoomCode(code);
  return useQuery({
    queryKey: roomQueryKey(roomCode),
    queryFn: ({ signal }) => {
      if (viewer === 'account') return enterRoom(roomCode, signal);
      if (guestToken !== null) return restoreGuestSession(roomCode, guestToken, signal);
      return getRoom(roomCode, signal);
    },
    enabled: viewer !== undefined,
    retry: shouldRetry,
  });
}

// Crée une salle à partir d'un template (US-2.1) ; l'utilisateur en devient le room admin
export function useCreateRoom(): UseMutationResult<Room, Error, CreateRoomRequest> {
  const queryClient: QueryClient = useQueryClient();
  return useMutation({
    mutationFn: createRoom,
    onSuccess: (room: Room) => storeRoom(queryClient, room),
  });
}

// Entre dans la salle en invité avec un pseudo (US-2.5) ; le backend pose le cookie qui le fait
// reconnaître et renvoie son lien perso
export function useJoinAsGuest(
  code: string,
): UseMutationResult<GuestRoom, Error, JoinAsGuestRequest> {
  const queryClient: QueryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: JoinAsGuestRequest) => joinAsGuest(canonicalRoomCode(code), body),
    onSuccess: (guestRoom: GuestRoom) => storeRoom(queryClient, guestRoom),
  });
}

// Nouveau lien perso pour l'invité reconnu par son cookie ; l'ancien cesse de marcher
export function useRenewGuestLink(code: string): UseMutationResult<GuestRoom, Error, void> {
  const queryClient: QueryClient = useQueryClient();
  return useMutation({
    mutationFn: () => renewGuestLink(canonicalRoomCode(code)),
    onSuccess: (guestRoom: GuestRoom) => storeRoom(queryClient, guestRoom),
  });
}

// Réglages de la prochaine partie (US-2.2), réservés au room admin
export function useUpdateRoomSettings(
  code: string,
): UseMutationResult<Room, Error, RoomSettingsChanges> {
  const queryClient: QueryClient = useQueryClient();
  return useMutation({
    mutationFn: (changes: RoomSettingsChanges) =>
      updateRoomSettings(canonicalRoomCode(code), changes),
    onSuccess: (room: Room) => storeRoom(queryClient, room),
  });
}

export interface RemoveParticipantRequest {
  participantId: string;
  ban: boolean;
}

// Retire (ou bannit) un participant, réservé au room admin
export function useRemoveParticipant(
  code: string,
): UseMutationResult<Room, Error, RemoveParticipantRequest> {
  const queryClient: QueryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ participantId, ban }: RemoveParticipantRequest) =>
      removeParticipant(canonicalRoomCode(code), participantId, ban),
    onSuccess: (room: Room) => storeRoom(queryClient, room),
  });
}

// Lève un bannissement, réservé au room admin : la personne peut rejoindre à nouveau
export function useUnban(code: string): UseMutationResult<Room, Error, string> {
  const queryClient: QueryClient = useQueryClient();
  return useMutation({
    mutationFn: (banId: string) => unban(canonicalRoomCode(code), banId),
    onSuccess: (room: Room) => storeRoom(queryClient, room),
  });
}
