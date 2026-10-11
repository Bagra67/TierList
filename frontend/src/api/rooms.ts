import {
  type QueryClient,
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';

import { roomQueryKey } from '../constants/rooms';
import { apiClient, dataOrThrow } from './client';
import type { components } from './schema';

export type Room = components['schemas']['RoomResponse'];
export type RoomSettings = components['schemas']['RoomSettingsResponse'];
export type ItemOrder = components['schemas']['ItemOrder'];
export type AutoAdvance = components['schemas']['AutoAdvance'];
type CreateRoomRequest = components['schemas']['CreateRoomRequest'];
// Réglages à changer : ceux qui sont absents restent tels quels
export type RoomSettingsChanges = components['schemas']['UpdateRoomSettingsRequest'];

async function createRoom(body: CreateRoomRequest): Promise<Room> {
  return dataOrThrow(await apiClient.POST('/rooms', { body }));
}

async function getRoom(code: string, signal?: AbortSignal): Promise<Room> {
  return dataOrThrow(await apiClient.GET('/rooms/{code}', { params: { path: { code } }, signal }));
}

async function updateRoomSettings(code: string, changes: RoomSettingsChanges): Promise<Room> {
  return dataOrThrow(
    await apiClient.PATCH('/rooms/{code}/settings', {
      params: { path: { code } },
      body: changes,
    }),
  );
}

// La salle renvoyée par une création ou une modification remplace celle du cache : le lobby
// l'affiche sans nouvelle lecture
function storeRoom(queryClient: QueryClient, room: Room): void {
  queryClient.setQueryData(roomQueryKey(room.code), room);
}

export function useRoom(code: string): UseQueryResult<Room> {
  return useQuery({
    queryKey: roomQueryKey(code),
    queryFn: ({ signal }) => getRoom(code, signal),
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

// Réglages de la prochaine partie (US-2.2), réservés au room admin
export function useUpdateRoomSettings(
  code: string,
): UseMutationResult<Room, Error, RoomSettingsChanges> {
  const queryClient: QueryClient = useQueryClient();
  return useMutation({
    mutationFn: (changes: RoomSettingsChanges) => updateRoomSettings(code, changes),
    onSuccess: (room: Room) => storeRoom(queryClient, room),
  });
}
