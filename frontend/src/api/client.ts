import createClient from 'openapi-fetch';

import { SESSION_PATHS } from '../constants/auth';
import { HTTP_STATUS } from '../constants/http';
import { ApiError } from '../errors/apiError';
import type { paths } from './schema';

// Client HTTP commun : chemins, paramètres et réponses typés par schema.d.ts (pnpm gen:api).
// '/api' est redirigé vers le backend FastAPI par le proxy Vite (vite.config.ts).
export const apiClient = createClient<paths>({
  // URL absolue : openapi-fetch crée un Request, que Node (tests) refuse avec une URL relative
  baseUrl: `${window.location.origin}/api`,
  // openapi-fetch mémorise fetch à la création : on le résout à chaque appel pour pouvoir le remplacer dans les tests
  fetch: (request) => fetch(request),
});

// Résultat d'un appel apiClient : data en cas de succès, sinon error (corps de la réponse)
interface ApiResult<T> {
  data?: T;
  error?: unknown;
  response: Response;
}

// Corps d'une réponse réussie ; lève ApiError pour toute réponse hors 2xx.
export function dataOrThrow<T>({ data, error, response }: ApiResult<T>): T {
  if (data === undefined) {
    throw new ApiError(response.status, error);
  }
  return data;
}

// Pour les réponses sans corps (ex. 204) : lève ApiError si la réponse n'est pas un succès.
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

export function hasAccessToken(): boolean {
  return accessToken !== null;
}

let refreshInFlight: Promise<boolean> | null = null;

// Renvoie false si la session est expirée (401), lève ApiError si le backend est injoignable.
// Un seul rafraîchissement à la fois : le backend révoque toute la session si le même
// refresh token est présenté deux fois (détection de vol).
export function refreshAccessToken(): Promise<boolean> {
  refreshInFlight ??= apiClient
    .POST('/auth/refresh')
    .then(({ data, error, response }) => {
      setAccessToken(data?.access_token ?? null);
      if (data === undefined && response.status !== HTTP_STATUS.UNAUTHORIZED) {
        throw new ApiError(response.status, error);
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
