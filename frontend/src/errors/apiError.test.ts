import { describe, expect, it } from 'vitest';

import { ApiError, getFieldErrors } from './apiError';

describe('getFieldErrors', () => {
  it('maps validation errors to body field names', () => {
    const error = new ApiError(422, {
      detail: 'Requête invalide',
      errors: [{ field: 'body.email', message: 'value is not a valid email address' }],
    });

    expect(getFieldErrors(error)).toEqual({ email: 'value is not a valid email address' });
  });

  it('returns no field error for other errors', () => {
    expect(getFieldErrors(new ApiError(500, 'Bad Gateway'))).toEqual({});
    expect(getFieldErrors(null)).toEqual({});
  });
});
