import type { TFunction } from 'i18next';

import type { components } from '../api/schema';
import { GATEWAY_ERROR_STATUSES } from '../constants/http';
import { hasTranslation } from '../i18n/hasTranslation';
import { fr } from '../i18n/locales/fr';

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

export class ApiError extends Error {
  readonly status: number;
  readonly body: unknown;
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

export function hasNoFieldError(error: unknown): boolean {
  return Object.keys(getFieldErrors(error)).length === 0;
}

function withDates(params: ErrorParams): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(params).map(([name, value]) => [
      name,
      name.endsWith('_at') && typeof value === 'string' ? new Date(value) : value,
    ]),
  );
}

function withLengthAsPluralCount(
  params: ErrorParams | null | undefined,
): ErrorParams | null | undefined {
  const length: unknown = params?.min_length ?? params?.max_length;
  return typeof length === 'number' ? { ...params, count: length } : params;
}

type TranslateRuntimeKey = (key: string, params: Record<string, unknown>) => string;

function translateCheckedKeyWithRuntimeParams(
  t: TFunction,
  key: string,
  params: ErrorParams | null | undefined,
) {
  return (t as TranslateRuntimeKey)(key, withDates(params ?? {}));
}

export function translateError(t: TFunction, error: unknown): string {
  if (!(error instanceof ApiError)) return t('common.backendUnreachable');
  if (error.code === undefined) {
    return GATEWAY_ERROR_STATUSES.has(error.status)
      ? t('common.backendUnreachable')
      : t('errors.unknown');
  }
  if (hasTranslation(fr.errors.api, error.code)) {
    return translateCheckedKeyWithRuntimeParams(t, `errors.api.${error.code}`, error.params);
  }
  return t('errors.unknown');
}

export function translateFieldError(
  t: TFunction,
  fieldError: FieldError | undefined,
): string | undefined {
  if (fieldError === undefined) return undefined;
  if (hasTranslation(fr.errors.field, fieldError.code)) {
    return translateCheckedKeyWithRuntimeParams(
      t,
      `errors.field.${fieldError.code}`,
      withLengthAsPluralCount(fieldError.params),
    );
  }
  return t('errors.field.invalid');
}
