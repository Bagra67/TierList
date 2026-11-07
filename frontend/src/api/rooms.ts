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
import { apiClient, dataOrThrow, throwIfError } from './client';
import { retryUnlessClientError } from './queryClient';
import type { components } from './schema';

export type Room = components['schemas']['RoomResponse'];
export type Participant = components['schemas']['ParticipantResponse'];
export type RoomBan = components['schemas']['RoomBanResponse'];
export type GuestRoom = components['schemas']['GuestRoomResponse'];
export type RoomSettings = components['schemas']['RoomSettingsResponse'];
export type ItemOrder = components['schemas']['ItemOrder'];
export type AutoAdvance = components['schemas']['AutoAdvance'];
type CreateRoomRequest = components['schemas']['CreateRoomRequest'];
type JoinAsGuestRequest = components['schemas']['JoinAsGuestRequest'];
export type RoomSettingsChanges = components['schemas']['UpdateRoomSettingsRequest'];
export type CurrentGame = components['schemas']['CurrentGameResponse'];
export type GameItem = components['schemas']['CurrentItemResponse'];
export type PastGame = components['schemas']['PastGameResponse'];
export type GameTier = components['schemas']['GameTierResponse'];
export type OwnPlacement = components['schemas']['OwnPlacementResponse'];

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

async function renewGuestLink(code: string): Promise<GuestRoom> {
  return dataOrThrow(
    await apiClient.POST('/rooms/{code}/guest-link', { params: { path: { code } } }),
  );
}

async function enterRoom(code: string, signal?: AbortSignal): Promise<Room> {
  try {
    return await getRoom(code, signal);
  } catch (error) {
    if (error instanceof ApiError && error.code === 'room_not_joined') {
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

async function closeRoom(code: string): Promise<void> {
  throwIfError(await apiClient.DELETE('/rooms/{code}', { params: { path: { code } } }));
}

async function startGame(code: string): Promise<Room> {
  return dataOrThrow(await apiClient.POST('/rooms/{code}/game', { params: { path: { code } } }));
}

async function placeItem(code: string, request: PlaceItemRequest): Promise<Room> {
  return dataOrThrow(
    await apiClient.PUT('/rooms/{code}/game/placements/{tile_id}', {
      params: { path: { code, tile_id: request.tileId } },
      body: { tier_id: request.tierId, position: request.position },
    }),
  );
}

async function nextRound(code: string): Promise<Room> {
  return dataOrThrow(
    await apiClient.POST('/rooms/{code}/game/next', { params: { path: { code } } }),
  );
}

async function endCooldown(code: string): Promise<Room> {
  return dataOrThrow(
    await apiClient.POST('/rooms/{code}/game/end', { params: { path: { code } } }),
  );
}

function storeRoom(queryClient: QueryClient, room: Room): void {
  const cached: Room | undefined = queryClient.getQueryData<Room>(roomQueryKey(room.code));
  if (cached !== undefined && isOlder(room, cached)) {
    void queryClient.invalidateQueries({ queryKey: roomQueryKey(room.code) });
    return;
  }
  queryClient.setQueryData(roomQueryKey(room.code), room);
}

const GAME_STATUS_ORDER: Record<CurrentGame['status'], number> = {
  in_round: 0,
  cooldown: 1,
  closed: 2,
};

function isOlder(room: Room, cached: Room): boolean {
  if (room.version !== cached.version) return room.version < cached.version;
  if (room.game === null || cached.game === null) return false;
  if (room.game.status !== cached.game.status) {
    return GAME_STATUS_ORDER[room.game.status] < GAME_STATUS_ORDER[cached.game.status];
  }
  return room.game.round_number < cached.game.round_number;
}

export type RoomViewer = 'account' | 'guest';

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
    retry: retryUnlessClientError,
  });
}

export function useCreateRoom(): UseMutationResult<Room, Error, CreateRoomRequest> {
  const queryClient: QueryClient = useQueryClient();
  return useMutation({
    mutationFn: createRoom,
    onSuccess: (room: Room) => storeRoom(queryClient, room),
  });
}

export function useJoinAsGuest(
  code: string,
): UseMutationResult<GuestRoom, Error, JoinAsGuestRequest> {
  const queryClient: QueryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: JoinAsGuestRequest) => joinAsGuest(canonicalRoomCode(code), body),
    onSuccess: (guestRoom: GuestRoom) => storeRoom(queryClient, guestRoom),
  });
}

export function useRenewGuestLink(code: string): UseMutationResult<GuestRoom, Error, void> {
  const queryClient: QueryClient = useQueryClient();
  return useMutation({
    mutationFn: () => renewGuestLink(canonicalRoomCode(code)),
    onSuccess: (guestRoom: GuestRoom) => storeRoom(queryClient, guestRoom),
  });
}

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

export function useUnban(code: string): UseMutationResult<Room, Error, string> {
  const queryClient: QueryClient = useQueryClient();
  return useMutation({
    mutationFn: (banId: string) => unban(canonicalRoomCode(code), banId),
    onSuccess: (room: Room) => storeRoom(queryClient, room),
  });
}

export function useStartGame(code: string): UseMutationResult<Room, Error, void> {
  const queryClient: QueryClient = useQueryClient();
  return useMutation({
    mutationFn: () => startGame(canonicalRoomCode(code)),
    onSuccess: (room: Room) => storeRoom(queryClient, room),
  });
}

export interface PlaceItemRequest {
  tileId: string;
  tierId: string;
  position: number;
}

export function usePlaceItem(code: string): UseMutationResult<Room, Error, PlaceItemRequest> {
  const queryClient: QueryClient = useQueryClient();
  return useMutation({
    mutationFn: (request: PlaceItemRequest) => placeItem(canonicalRoomCode(code), request),
    onSuccess: (room: Room) => storeRoom(queryClient, room),
  });
}

export function useNextRound(code: string): UseMutationResult<Room, Error, void> {
  const queryClient: QueryClient = useQueryClient();
  return useMutation({
    mutationFn: () => nextRound(canonicalRoomCode(code)),
    onSuccess: (room: Room) => storeRoom(queryClient, room),
  });
}

export function useCloseRoom(code: string): UseMutationResult<void, Error, void> {
  return useMutation({ mutationFn: () => closeRoom(canonicalRoomCode(code)) });
}

export function useEndCooldown(code: string): UseMutationResult<Room, Error, void> {
  const queryClient: QueryClient = useQueryClient();
  return useMutation({
    mutationFn: () => endCooldown(canonicalRoomCode(code)),
    onSuccess: (room: Room) => storeRoom(queryClient, room),
  });
}
