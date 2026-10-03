import type { components } from '../api/schema';

// Format unique des erreurs du backend (app/core/errors.py)
export type ErrorResponse = components['schemas']['ErrorResponse'];

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
