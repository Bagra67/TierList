import {
  hashKey,
  type QueryClient,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import { useEffect } from 'react';

import {
  CURRENT_USER_QUERY_KEY,
  GOOGLE_BAN_NOTICE_QUERY_KEY,
  GOOGLE_ACCOUNT_BANNED,
  GOOGLE_SIGN_IN_PATH,
  type GoogleNextStep,
} from '../constants/auth';
import { HTTP_STATUS } from '../constants/http';
import { ROOMS_QUERY_KEY } from '../constants/rooms';
import { ApiError } from '../errors/apiError';
import { currentLanguage } from '../i18n';
import {
  apiClient,
  dataOrThrow,
  hasAccessToken,
  onSessionEnded,
  refreshAccessToken,
  setAccessToken,
  throwIfError,
} from './client';
import { retryUnlessClientError } from './queryClient';
import type { components } from './schema';

type RegisterRequest = Omit<components['schemas']['RegisterRequest'], 'language'>;
export type LoginRequest = components['schemas']['LoginRequest'];
export type User = components['schemas']['UserResponse'];
export type DeleteAccountRequest = components['schemas']['DeleteAccountRequest'];
type ResetPasswordRequest = components['schemas']['ResetPasswordRequest'];

export function googleSignInUrl(next?: GoogleNextStep): string {
  const query = next === undefined ? '' : `?${new URLSearchParams({ next }).toString()}`;
  return `${GOOGLE_SIGN_IN_PATH}${query}`;
}

export function useGoogleBanNotice(googleError: string | null) {
  return useQuery({
    queryKey: GOOGLE_BAN_NOTICE_QUERY_KEY,
    queryFn: async ({ signal }): Promise<null> => {
      throwIfError(await apiClient.GET('/auth/google/ban-notice', { signal }));
      return null;
    },
    enabled: googleError === GOOGLE_ACCOUNT_BANNED,
    retry: retryUnlessClientError,
  });
}

async function register(body: RegisterRequest): Promise<void> {
  const data = dataOrThrow(
    await apiClient.POST('/auth/register', { body: { ...body, language: currentLanguage() } }),
  );
  setAccessToken(data.access_token);
}

export async function login(body: LoginRequest): Promise<void> {
  const data = dataOrThrow(await apiClient.POST('/auth/login', { body }));
  setAccessToken(data.access_token);
}

export async function logout(): Promise<void> {
  setAccessToken(null);
  throwIfError(await apiClient.POST('/auth/logout'));
}

export async function deleteAccount(body: DeleteAccountRequest): Promise<void> {
  throwIfError(await apiClient.DELETE('/auth/me', { body }));
  setAccessToken(null);
}

async function verifyEmail(token: string): Promise<void> {
  throwIfError(await apiClient.POST('/auth/email/verify', { body: { token } }));
}

async function requestEmailVerification(): Promise<void> {
  throwIfError(
    await apiClient.POST('/auth/email/verification', {
      body: { language: currentLanguage() },
    }),
  );
}

async function forgotPassword(email: string): Promise<void> {
  throwIfError(
    await apiClient.POST('/auth/password/forgot', {
      body: { email, language: currentLanguage() },
    }),
  );
}

async function resetPassword(body: ResetPasswordRequest): Promise<void> {
  throwIfError(await apiClient.POST('/auth/password/reset', { body }));
}

export async function getMe(signal?: AbortSignal): Promise<User> {
  return dataOrThrow(await apiClient.GET('/auth/me', { signal }));
}

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

function refetchWhileEmailUnverified(query: {
  state: { data: User | null | undefined };
}): boolean | 'always' {
  return query.state.data?.email_verified === false ? 'always' : false;
}

interface CurrentUserOptions {
  refreshUntilEmailVerified?: boolean;
}

export function useCurrentUser({ refreshUntilEmailVerified = false }: CurrentUserOptions = {}) {
  return useQuery({
    queryKey: CURRENT_USER_QUERY_KEY,
    queryFn: ({ signal }) => getCurrentUser(signal),
    staleTime: Infinity,
    ...(refreshUntilEmailVerified && {
      refetchOnMount: refetchWhileEmailUnverified,
      refetchOnWindowFocus: refetchWhileEmailUnverified,
    }),
  });
}

function startSession(queryClient: QueryClient): Promise<void> {
  queryClient.removeQueries({ queryKey: ROOMS_QUERY_KEY });
  return queryClient.invalidateQueries({ queryKey: CURRENT_USER_QUERY_KEY });
}

export function useRegister() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: register,
    onSuccess: () => startSession(queryClient),
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: login,
    onSuccess: () => startSession(queryClient),
  });
}

export function useVerifyEmail() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: verifyEmail,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CURRENT_USER_QUERY_KEY }),
  });
}

export function useRequestEmailVerification() {
  return useMutation({ mutationFn: requestEmailVerification });
}

function forgetSession(queryClient: QueryClient): void {
  const currentUserHash: string = hashKey(CURRENT_USER_QUERY_KEY);
  queryClient.setQueryData(CURRENT_USER_QUERY_KEY, null);
  queryClient.removeQueries({ predicate: (query) => query.queryHash !== currentUserHash });
  queryClient.getMutationCache().clear();
}

export function useForgetEndedSession(): void {
  const queryClient: QueryClient = useQueryClient();
  useEffect(() => onSessionEnded(() => forgetSession(queryClient)), [queryClient]);
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: logout,
    onSettled: () => forgetSession(queryClient),
  });
}

export function useForgotPassword() {
  return useMutation({ mutationFn: forgotPassword });
}

export function useResetPassword() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: resetPassword,
    onSuccess: () => {
      setAccessToken(null);
      forgetSession(queryClient);
    },
  });
}

export function useDeleteAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteAccount,
    onSuccess: () => forgetSession(queryClient),
  });
}
