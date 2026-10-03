import type { TFunction } from 'i18next';

import type { components } from '../api/schema';
import { hasTranslation } from '../i18n/hasTranslation';
import { fr } from '../i18n/locales/fr';

// Format unique des erreurs du backend (app/core/errors.py)
export type ErrorResponse = components['schemas']['ErrorResponse'];
export type FieldError = components['schemas']['FieldError'];
type ErrorParams = NonNullable<ErrorResponse['params']>;

function isErrorResponse(body: unknown): body is ErrorResponse {
  return (
    typeof body === 'object' &&
    body !== null &&
    typeof (body as ErrorResponse).detail === 'string' &&
    typeof (body as ErrorResponse).code === 'string'
  );
}

// Levée quand le backend répond avec un statut hors 2xx. Le corps n'est pas garanti
// (ex. : page d'erreur du proxy quand le backend est arrêté), d'où `unknown`.
// Le message (detail, en anglais) sert au diagnostic : l'interface affiche translateError().
export class ApiError extends Error {
  readonly status: number;
  readonly body: unknown;
  // Code d'erreur de l'API, absent si le corps n'est pas au format ErrorResponse
  readonly code: string | undefined;
  readonly params: ErrorParams | undefined;

  constructor(status: number, body: unknown) {
    const errorResponse = isErrorResponse(body) ? body : undefined;
    super(errorResponse?.detail ?? `HTTP ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
    this.code = errorResponse?.code;
    this.params = errorResponse?.params ?? undefined;
  }
}

// Erreurs de validation (422) par champ du corps : « body.email » → « email »
export function getFieldErrors(error: unknown): Record<string, FieldError> {
  if (!(error instanceof ApiError) || !isErrorResponse(error.body)) {
    return {};
  }
  return Object.fromEntries(
    (error.body.errors ?? []).map((fieldError) => [
      fieldError.field.replace(/^body\./, ''),
      fieldError,
    ]),
  );
}

// Les params viennent du backend : connus seulement à l'exécution, ils ne peuvent pas être
// vérifiés au typage contre les variables du texte. L'appelant vérifie la clé au préalable.
function translateWithParams(t: TFunction, key: string, params: ErrorParams | null | undefined) {
  return (t as (key: string, params: ErrorParams) => string)(key, params ?? {});
}

// Message à afficher pour une erreur de requête, dans la langue de l'interface
export function translateError(t: TFunction, error: unknown): string {
  if (!(error instanceof ApiError) || error.code === undefined) {
    // Erreur réseau, ou réponse qui ne vient pas du backend (proxy sans backend derrière)
    return t('common.backendUnreachable');
  }
  if (hasTranslation(fr.errors.api, error.code)) {
    return translateWithParams(t, `errors.api.${error.code}`, error.params);
  }
  return t('errors.unknown');
}

// Message à afficher sous un champ invalide ; un type d'erreur sans traduction dédiée
// (Pydantic en a beaucoup) donne un message générique.
export function translateFieldError(
  t: TFunction,
  fieldError: FieldError | undefined,
): string | undefined {
  if (fieldError === undefined) return undefined;
  if (hasTranslation(fr.errors.field, fieldError.code)) {
    return translateWithParams(t, `errors.field.${fieldError.code}`, fieldError.params);
  }
  return t('errors.field.invalid');
}
