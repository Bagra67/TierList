import { type QueryClient, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  CURRENT_USER_QUERY_KEY,
  GOOGLE_SIGN_IN_PATH,
  type GoogleNextStep,
} from '../constants/auth';
import { HTTP_STATUS } from '../constants/http';
import { ApiError } from '../errors/apiError';
import { currentLanguage } from '../i18n';
import { apiClient, hasAccessToken, refreshAccessToken, setAccessToken } from './client';
import type { components } from './schema';

// La langue de l'email de vérification est ajoutée ici : les pages n'ont pas à la fournir
export type RegisterRequest = Omit<components['schemas']['RegisterRequest'], 'language'>;
export type LoginRequest = components['schemas']['LoginRequest'];
export type User = components['schemas']['UserResponse'];
export type DeleteAccountRequest = components['schemas']['DeleteAccountRequest'];

// Connexion avec Google : navigation complète (pas un appel fetch), le backend redirige vers
// Google puis, au retour, vers le frontend avec le cookie de session posé.
export function googleSignInUrl(next?: GoogleNextStep): string {
  const query = next === undefined ? '' : `?${new URLSearchParams({ next }).toString()}`;
  return `${GOOGLE_SIGN_IN_PATH}${query}`;
}

export async function register(body: RegisterRequest): Promise<void> {
  const { data, error, response } = await apiClient.POST('/auth/register', {
    body: { ...body, language: currentLanguage() },
  });
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

export async function deleteAccount(body: DeleteAccountRequest): Promise<void> {
  const { response, error } = await apiClient.DELETE('/auth/me', { body });
  if (!response.ok) {
    throw new ApiError(response.status, error);
  }
  setAccessToken(null);
}

// Confirme l'adresse avec le token du lien reçu par email (sans session : le lien peut être
// ouvert dans un autre navigateur)
export async function verifyEmail(token: string): Promise<void> {
  const { response, error } = await apiClient.POST('/auth/email/verify', { body: { token } });
  if (!response.ok) {
    throw new ApiError(response.status, error);
  }
}

// Renvoie l'email de vérification ; le backend l'ignore si le précédent est trop récent
export async function requestEmailVerification(): Promise<void> {
  const { response, error } = await apiClient.POST('/auth/email/verification', {
    body: { language: currentLanguage() },
  });
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
    if (error instanceof ApiError && error.status === HTTP_STATUS.UNAUTHORIZED) {
      return null;
    }
    throw error;
  }
}

export function useCurrentUser() {
  return useQuery({
    queryKey: CURRENT_USER_QUERY_KEY,
    queryFn: ({ signal }) => getCurrentUser(signal),
    // L'utilisateur ne change qu'à la connexion / déconnexion, qui mettent ce cache à jour
    staleTime: Infinity,
  });
}

export function useRegister() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: register,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CURRENT_USER_QUERY_KEY }),
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: login,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CURRENT_USER_QUERY_KEY }),
  });
}

export function useVerifyEmail() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: verifyEmail,
    // Utilisateur connecté dans ce navigateur : son adresse apparaît désormais comme confirmée
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CURRENT_USER_QUERY_KEY }),
  });
}

export function useRequestEmailVerification() {
  return useMutation({ mutationFn: requestEmailVerification });
}

// Après déconnexion ou suppression : aucune donnée de l'ancien utilisateur ne reste en cache
function forgetSession(queryClient: QueryClient): void {
  queryClient.clear();
  queryClient.setQueryData(CURRENT_USER_QUERY_KEY, null);
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: logout,
    // Même en cas d'échec réseau, l'interface repasse en mode déconnecté
    onSettled: () => forgetSession(queryClient),
  });
}

export function useDeleteAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteAccount,
    onSuccess: () => forgetSession(queryClient),
  });
}
