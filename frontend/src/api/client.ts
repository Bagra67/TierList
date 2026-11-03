import createClient from 'openapi-fetch';

import { SESSION_PATHS } from '../constants/auth';
import { HTTP_STATUS } from '../constants/http';
import { ApiError } from '../errors/apiError';
import type { paths } from './schema';

export const apiClient = createClient<paths>({
  baseUrl: `${window.location.origin}/api`,
  fetch: (request) => fetch(request),
});

interface ApiResult<T> {
  data?: T;
  error?: unknown;
  response: Response;
}

export function dataOrThrow<T>({ data, error, response }: ApiResult<T>): T {
  if (data === undefined) {
    throw new ApiError(response.status, error);
  }
  return data;
}

export function throwIfError({ error, response }: ApiResult<unknown>): void {
  if (!response.ok) {
    throw new ApiError(response.status, error);
  }
}

// Access token (JWT, ~15 min) gardé en mémoire seulement : jamais dans localStorage, lisible
// par un script injecté. Le refresh token, lui, est un cookie HttpOnly géré par le navigateur.
let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function hasAccessToken(): boolean {
  return accessToken !== null;
}

const sessionEndedListeners = new Set<() => void>();

export function onSessionEnded(listener: () => void): () => void {
  sessionEndedListeners.add(listener);
  return () => {
    sessionEndedListeners.delete(listener);
  };
}

let refreshInFlight: Promise<boolean> | null = null;

export function refreshAccessToken(): Promise<boolean> {
  const hadSession: boolean = accessToken !== null;
  refreshInFlight ??= apiClient
    .POST('/auth/refresh')
    .then(({ data, error, response }) => {
      setAccessToken(data?.access_token ?? null);
      if (data === undefined && response.status !== HTTP_STATUS.UNAUTHORIZED) {
        throw new ApiError(response.status, error);
      }
      if (data === undefined && hadSession) {
        sessionEndedListeners.forEach((listener) => listener());
      }
      return data !== undefined;
    })
    .finally(() => {
      refreshInFlight = null;
    });
  return refreshInFlight;
}

// Copies des requêtes en cours : le corps d'une Request ne peut être lu qu'une fois,
// il en faut une copie intacte pour la renvoyer après un rafraîchissement.
const pendingRequests = new Map<string, Request>();

apiClient.use({
  onRequest({ request, id }) {
    if (accessToken !== null) {
      request.headers.set('Authorization', `Bearer ${accessToken}`);
    }
    pendingRequests.set(id, request.clone());
    return request;
  },
  async onResponse({ response, schemaPath, id }) {
    const original = pendingRequests.get(id);
    pendingRequests.delete(id);
    if (
      response.status !== HTTP_STATUS.UNAUTHORIZED ||
      SESSION_PATHS.has(schemaPath) ||
      original === undefined
    ) {
      return response;
    }
    if (!(await refreshAccessToken())) {
      return response;
    }
    original.headers.set('Authorization', `Bearer ${accessToken}`);
    return fetch(original);
  },
  onError({ id }) {
    pendingRequests.delete(id);
  },
});
