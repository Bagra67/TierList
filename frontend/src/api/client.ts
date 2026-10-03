import createClient from 'openapi-fetch';

import type { components, paths } from './schema';

// Format unique des erreurs du backend (app/core/errors.py)
export type ErrorResponse = components['schemas']['ErrorResponse'];

// Client HTTP commun : chemins, paramètres et réponses typés par schema.d.ts (pnpm gen:api).
// '/api' est redirigé vers le backend FastAPI par le proxy Vite (vite.config.ts).
export const apiClient = createClient<paths>({
  // URL absolue : openapi-fetch crée un Request, que Node (tests) refuse avec une URL relative
  baseUrl: `${window.location.origin}/api`,
  // openapi-fetch mémorise fetch à la création : on le résout à chaque appel pour pouvoir le remplacer dans les tests
  fetch: (request) => fetch(request),
});

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
      if (data === undefined && response.status !== 401) {
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

// Routes qui ouvrent ou ferment la session : leur 401 (identifiants faux, session expirée)
// est la réponse attendue, il ne faut pas tenter de rafraîchir (ni boucler sur /auth/refresh).
const SESSION_PATHS = new Set(['/auth/register', '/auth/login', '/auth/refresh', '/auth/logout']);

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
    if (response.status !== 401 || SESSION_PATHS.has(schemaPath) || original === undefined) {
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

function isErrorResponse(body: unknown): body is ErrorResponse {
  return (
    typeof body === 'object' && body !== null && typeof (body as ErrorResponse).detail === 'string'
  );
}

// Levée quand le backend répond avec un statut hors 2xx. Le corps n'est pas garanti
// (ex. : page d'erreur du proxy quand le backend est arrêté), d'où `unknown`.
export class ApiError extends Error {
  readonly status: number;
  readonly body: unknown;

  constructor(status: number, body: unknown) {
    super(isErrorResponse(body) ? body.detail : `HTTP ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

// Messages des erreurs de validation (422) par champ du corps : « body.email » → « email »
export function getFieldErrors(error: unknown): Record<string, string> {
  if (!(error instanceof ApiError) || !isErrorResponse(error.body)) {
    return {};
  }
  return Object.fromEntries(
    (error.body.errors ?? []).map(({ field, message }) => [field.replace(/^body\./, ''), message]),
  );
}
