import { describe, expect, it } from 'vitest';

import i18n from '../i18n';
import { ApiError, getFieldErrors, translateError, translateFieldError } from './apiError';

const emailError = {
  field: 'body.email',
  message: 'value is not a valid email address',
  code: 'value_error',
};
const shortPasswordError = {
  field: 'body.password',
  message: 'The password must be at least 12 characters long',
  code: 'password_too_short',
  params: { min_length: 12 },
};
const validationError = new ApiError(422, {
  detail: 'Invalid request',
  code: 'validation_error',
  errors: [emailError, shortPasswordError],
});

describe('ApiError', () => {
  it('exposes the code, the params and the detail as its message', () => {
    const error = new ApiError(401, {
      detail: 'Authentication required',
      code: 'not_authenticated',
      params: { retry_after: 30 },
    });

    expect(error).toMatchObject({
      status: 401,
      code: 'not_authenticated',
      params: { retry_after: 30 },
      message: 'Authentication required',
    });
  });

  it('has no code when the body is not an ErrorResponse', () => {
    const error = new ApiError(502, 'Bad Gateway');

    expect(error).toMatchObject({ status: 502, code: undefined, message: 'HTTP 502' });
  });
});

describe('getFieldErrors', () => {
  it('maps validation errors to body field names', () => {
    expect(getFieldErrors(validationError)).toEqual({
      email: emailError,
      password: shortPasswordError,
    });
  });

  it('returns no field error for other errors', () => {
    expect(getFieldErrors(new ApiError(500, 'Bad Gateway'))).toEqual({});
    expect(getFieldErrors(null)).toEqual({});
  });
});

describe('translateError', () => {
  it('translates the error code in the interface language', async () => {
    const error = new ApiError(401, { detail: 'Incorrect', code: 'invalid_credentials' });

    expect(translateError(i18n.t, error)).toBe('Email ou mot de passe incorrect');
    await i18n.changeLanguage('en');
    expect(translateError(i18n.t, error)).toBe('Incorrect email or password');
  });

  it('shows a size sent in bytes in megabytes, in the interface language', async () => {
    const error: ApiError = new ApiError(413, {
      detail: 'The file is larger than 10485760 bytes',
      code: 'image_too_large',
      params: { max_bytes: 10485760 },
    });

    // Intl sépare le nombre et l'unité par une espace insécable, selon la langue
    expect(translateError(i18n.t, error)).toMatch(
      /^L'image est trop lourde : 10\sMo au maximum\.$/,
    );
    await i18n.changeLanguage('en');
    expect(translateError(i18n.t, error)).toMatch(/^The image is too heavy: 10\sMB at most\.$/);
  });

  it('falls back to a generic message for an unknown code', () => {
    const error = new ApiError(418, { detail: "I'm a teapot", code: 'teapot' });

    expect(translateError(i18n.t, error)).toBe('Une erreur est survenue, veuillez réessayer.');
  });

  it('reports an unreachable backend when the response is not from the API', () => {
    expect(translateError(i18n.t, new ApiError(502, 'Bad Gateway'))).toBe(
      'Impossible de joindre le backend : est-il lancé ?',
    );
    expect(translateError(i18n.t, new TypeError('Failed to fetch'))).toBe(
      'Impossible de joindre le backend : est-il lancé ?',
    );
  });
});

describe('translateFieldError', () => {
  const fieldErrors = getFieldErrors(validationError);

  it('translates the field error code with its params', async () => {
    expect(translateFieldError(i18n.t, fieldErrors.password)).toBe(
      'Le mot de passe doit contenir au moins 12 caractères',
    );
    await i18n.changeLanguage('en');
    expect(translateFieldError(i18n.t, fieldErrors.password)).toBe(
      'The password must be at least 12 characters long',
    );
  });

  it('uses a generic message for a Pydantic error type without a dedicated text', () => {
    const fieldError = { field: 'body.email', message: '…', code: 'url_parsing' };

    expect(translateFieldError(i18n.t, fieldError)).toBe('Valeur invalide.');
  });

  it('returns nothing for a valid field', () => {
    expect(translateFieldError(i18n.t, fieldErrors.display_name)).toBeUndefined();
  });
});
