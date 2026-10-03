import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { ApiError, apiClient, hasAccessToken, refreshAccessToken, setAccessToken } from './client';
import type { components } from './schema';

export type RegisterRequest = components['schemas']['RegisterRequest'];
export type LoginRequest = components['schemas']['LoginRequest'];
export type User = components['schemas']['UserResponse'];

const currentUserKey = ['auth', 'me'] as const;

export async function register(body: RegisterRequest): Promise<void> {
  const { data, error, response } = await apiClient.POST('/auth/register', { body });
  if (data === undefined) {
    throw new ApiError(response.status, error);
  }
  setAccessToken(data.access_token);
}

export async function login(body: LoginRequest): Promise<void> {
  const { data, error, response } = await apiClient.POST('/auth/login', { body });
  if (data === undefined) {
    throw new ApiError(response.status, error);
  }
  setAccessToken(data.access_token);
}

export async function logout(): Promise<void> {
  // Le token en mémoire est oublié même si le backend est injoignable
  setAccessToken(null);
  const { response, error } = await apiClient.POST('/auth/logout');
  if (!response.ok) {
    throw new ApiError(response.status, error);
  }
}

export async function getMe(signal?: AbortSignal): Promise<User> {
  const { data, error, response } = await apiClient.GET('/auth/me', { signal });
  if (data === undefined) {
    throw new ApiError(response.status, error);
  }
  return data;
}

// Utilisateur connecté, ou null. Au chargement de la page, aucun access token n'est en mémoire :
// la session est restaurée grâce au cookie de refresh, s'il est encore valide.
export async function getCurrentUser(signal?: AbortSignal): Promise<User | null> {
  if (!hasAccessToken() && !(await refreshAccessToken())) {
    return null;
  }
  try {
    return await getMe(signal);
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return null;
    }
    throw error;
  }
}

export function useCurrentUser() {
  return useQuery({
    queryKey: currentUserKey,
    queryFn: ({ signal }) => getCurrentUser(signal),
    // L'utilisateur ne change qu'à la connexion / déconnexion, qui mettent ce cache à jour
    staleTime: Infinity,
  });
}

export function useRegister() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: register,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: currentUserKey }),
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: login,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: currentUserKey }),
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: logout,
    // Même en cas d'échec réseau, l'interface repasse en mode déconnecté
    onSettled: () => {
      queryClient.clear();
      queryClient.setQueryData(currentUserKey, null);
    },
  });
}
