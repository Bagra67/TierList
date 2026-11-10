import createClient from 'openapi-fetch';

import { SESSION_PATHS } from '../constants/auth';
import { HTTP_STATUS } from '../constants/http';
import { ApiError } from '../errors/apiError';
import { isAbortError, NetworkError } from '../errors/networkError';
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

let inMemoryAccessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  inMemoryAccessToken = token;
}

export function getAccessToken(): string | null {
  return inMemoryAccessToken;
}

export function hasAccessToken(): boolean {
  return inMemoryAccessToken !== null;
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
  const tokenBeforeRefresh: string | null = inMemoryAccessToken;
  refreshInFlight ??= apiClient
    .POST('/auth/refresh')
    .then(({ data, error, response }) => {
      if (data !== undefined) {
        setAccessToken(data.access_token);
        return true;
      }
      const hasNoSession: boolean =
        response.status === HTTP_STATUS.NO_CONTENT || response.status === HTTP_STATUS.UNAUTHORIZED;
      if (!hasNoSession) {
        throw new ApiError(response.status, error);
      }
      if (inMemoryAccessToken !== tokenBeforeRefresh) {
        return inMemoryAccessToken !== null;
      }
      setAccessToken(null);
      if (tokenBeforeRefresh !== null) {
        sessionEndedListeners.forEach((listener) => listener());
      }
      return false;
    })
    .finally(() => {
      refreshInFlight = null;
    });
  return refreshInFlight;
}

const requestCopiesForRetry = new Map<string, Request>();

apiClient.use({
  onRequest({ request, id }) {
    if (inMemoryAccessToken !== null) {
      request.headers.set('Authorization', `Bearer ${inMemoryAccessToken}`);
    }
    requestCopiesForRetry.set(id, request.clone());
    return request;
  },
  async onResponse({ response, schemaPath, id }) {
    const original = requestCopiesForRetry.get(id);
    requestCopiesForRetry.delete(id);
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
    original.headers.set('Authorization', `Bearer ${inMemoryAccessToken}`);
    try {
      return await fetch(original);
    } catch (error: unknown) {
      throw isAbortError(error) ? error : new NetworkError(error);
    }
  },
  onError({ id, error }) {
    requestCopiesForRetry.delete(id);
    return isAbortError(error) ? undefined : new NetworkError(error);
  },
});
