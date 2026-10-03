import { afterEach, describe, expect, it, vi } from 'vitest';

import { alice, calledRoutes, stubBackend, tokenResponse, unauthorized } from '../test/stubBackend';
import { getMe, login } from './auth';
import { ApiError, getFieldErrors, setAccessToken } from './client';

// Réponse de GET /auth/me qui n'accepte que l'access token donné
const meAcceptingOnly = (accessToken: string) => (request: Request) =>
  request.headers.get('Authorization') === `Bearer ${accessToken}`
    ? Response.json(alice)
    : unauthorized();

describe('apiClient authentication middleware', () => {
  afterEach(() => {
    setAccessToken(null);
    vi.unstubAllGlobals();
  });

  it('sends the access token in the Authorization header', async () => {
    stubBackend({ 'GET /auth/me': meAcceptingOnly('token-1') });
    setAccessToken('token-1');

    await expect(getMe()).resolves.toEqual(alice);
  });

  it('refreshes an expired access token once, then retries the request', async () => {
    const fetchMock = stubBackend({
      'GET /auth/me': meAcceptingOnly('token-2'),
      'POST /auth/refresh': tokenResponse('token-2'),
    });
    setAccessToken('expired-token');

    await expect(getMe()).resolves.toEqual(alice);
    expect(calledRoutes(fetchMock)).toEqual(['GET /auth/me', 'POST /auth/refresh', 'GET /auth/me']);
  });

  it('shares a single refresh between concurrent requests', async () => {
    const fetchMock = stubBackend({
      'GET /auth/me': meAcceptingOnly('token-2'),
      'POST /auth/refresh': tokenResponse('token-2'),
    });
    setAccessToken('expired-token');

    await Promise.all([getMe(), getMe()]);

    expect(calledRoutes(fetchMock).filter((route) => route === 'POST /auth/refresh')).toHaveLength(
      1,
    );
  });

  it('returns the 401 when the session cannot be refreshed', async () => {
    stubBackend({ 'GET /auth/me': unauthorized, 'POST /auth/refresh': unauthorized });
    setAccessToken('expired-token');

    const error = await getMe().catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 401 });
  });

  it('never refreshes on a 401 from a session route such as login', async () => {
    const fetchMock = stubBackend({
      'POST /auth/login': () =>
        Response.json({ detail: 'Email ou mot de passe incorrect' }, { status: 401 }),
    });
    setAccessToken('some-token');

    await expect(login({ email: 'alice@example.com', password: 'wrong' })).rejects.toThrow(
      'Email ou mot de passe incorrect',
    );
    expect(calledRoutes(fetchMock)).toEqual(['POST /auth/login']);
  });
});

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
