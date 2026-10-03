import { afterEach, describe, expect, it, vi } from 'vitest';

import { alice, calledRoutes, stubBackend, tokenResponse, unauthorized } from '../test/stubBackend';
import { getCurrentUser, getMe, login, logout } from './auth';
import { ApiError, setAccessToken } from './client';

describe('auth API', () => {
  afterEach(() => {
    setAccessToken(null);
    vi.unstubAllGlobals();
  });

  it('restores the session from the refresh cookie when no access token is in memory', async () => {
    const fetchMock = stubBackend({
      'POST /auth/refresh': tokenResponse('restored-token'),
      'GET /auth/me': () => Response.json(alice),
    });

    await expect(getCurrentUser()).resolves.toEqual(alice);
    expect(calledRoutes(fetchMock)).toEqual(['POST /auth/refresh', 'GET /auth/me']);
  });

  it('returns no user when there is no valid session', async () => {
    const fetchMock = stubBackend({ 'POST /auth/refresh': unauthorized });

    await expect(getCurrentUser()).resolves.toBeNull();
    expect(calledRoutes(fetchMock)).toEqual(['POST /auth/refresh']);
  });

  it('reports an unreachable backend instead of an anonymous user', async () => {
    stubBackend({ 'POST /auth/refresh': () => new Response('Bad Gateway', { status: 502 }) });

    const error = await getCurrentUser().catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 502 });
  });

  it('keeps the access token returned by login for the next requests', async () => {
    stubBackend({
      'POST /auth/login': tokenResponse('login-token'),
      'GET /auth/me': (request) =>
        request.headers.get('Authorization') === 'Bearer login-token'
          ? Response.json(alice)
          : unauthorized(),
    });

    await login({ email: 'alice@example.com', password: 'correct horse battery staple' });

    await expect(getMe()).resolves.toEqual(alice);
  });

  it('forgets the access token on logout, even if the backend fails', async () => {
    const fetchMock = stubBackend({
      'POST /auth/logout': () => new Response(null, { status: 500 }),
    });
    setAccessToken('some-token');

    await expect(logout()).rejects.toBeInstanceOf(ApiError);

    const logoutRequest = fetchMock.mock.calls[0][0];
    expect(logoutRequest.headers.get('Authorization')).toBeNull();
  });
});
