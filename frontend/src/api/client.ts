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
