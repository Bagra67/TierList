import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  alice,
  calledRoutes,
  errorResponse,
  stubBackend,
  tokenResponse,
  unauthorized,
} from '../test/stubBackend';
import { getMe, login } from './auth';
import { ApiError } from '../errors/apiError';
import { NetworkError } from '../errors/networkError';
import { getAccessToken, onSessionEnded, refreshAccessToken, setAccessToken } from './client';

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

  it('keeps a token set during a refresh that finds no session, without counting it as refreshed', async () => {
    let answerRefresh: ((response: Response) => void) | undefined;
    stubBackend({
      'POST /auth/refresh': () =>
        new Promise<Response>((resolve) => {
          answerRefresh = resolve;
        }),
    });

    const refreshed: Promise<boolean> = refreshAccessToken();
    await vi.waitFor(() => expect(answerRefresh).toBeDefined());
    setAccessToken('signed-in-meanwhile');
    answerRefresh?.(new Response(null, { status: 204 }));

    await expect(refreshed).resolves.toBe(false);
    expect(getAccessToken()).toBe('signed-in-meanwhile');
  });

  it('does not replay a request under a token set by a sign-in during its refresh', async () => {
    let answerRefresh: ((response: Response) => void) | undefined;
    const fetchMock = stubBackend({
      'GET /auth/me': unauthorized,
      'POST /auth/refresh': () =>
        new Promise<Response>((resolve) => {
          answerRefresh = resolve;
        }),
    });
    setAccessToken('expired-token');

    const read: Promise<unknown> = getMe().catch((caught: unknown) => caught);
    await vi.waitFor(() => expect(answerRefresh).toBeDefined());
    setAccessToken('signed-in-meanwhile');
    answerRefresh?.(unauthorized());

    await expect(read).resolves.toMatchObject({ status: 401 });
    expect(calledRoutes(fetchMock)).toEqual(['GET /auth/me', 'POST /auth/refresh']);
    expect(getAccessToken()).toBe('signed-in-meanwhile');
  });

  it('keeps the token when the refresh fails on the server side', async () => {
    stubBackend({ 'POST /auth/refresh': () => errorResponse(503, 'http_error') });
    setAccessToken('current-token');

    await expect(refreshAccessToken()).rejects.toBeInstanceOf(ApiError);
    expect(getAccessToken()).toBe('current-token');
  });

  it('never refreshes on a 401 from a session route such as login', async () => {
    const fetchMock = stubBackend({
      'POST /auth/login': () => errorResponse(401, 'invalid_credentials'),
    });
    setAccessToken('some-token');

    await expect(login({ email: 'alice@example.com', password: 'wrong' })).rejects.toThrow(
      expect.objectContaining({ status: 401, code: 'invalid_credentials' }),
    );
    expect(calledRoutes(fetchMock)).toEqual(['POST /auth/login']);
  });
});

describe('apiClient network failures', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('turns a lost connection into a NetworkError that keeps its cause', async () => {
    const lostConnection: TypeError = new TypeError('Failed to fetch');
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(lostConnection));

    const error = await getMe().catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(NetworkError);
    expect(error).toMatchObject({ cause: lostConnection });
  });

  it('turns a lost connection during the retry after a refresh into a NetworkError', async () => {
    const lostConnection: TypeError = new TypeError('Failed to fetch');
    let meCalls: number = 0;
    stubBackend({
      'GET /auth/me': () => {
        meCalls += 1;
        if (meCalls > 1) throw lostConnection;
        return unauthorized();
      },
      'POST /auth/refresh': tokenResponse('token-2'),
    });
    setAccessToken('expired-token');

    const error = await getMe().catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(NetworkError);
    expect(error).toMatchObject({ cause: lostConnection });
    setAccessToken(null);
  });

  it('leaves an aborted request as it is', async () => {
    const abort: DOMException = new DOMException('aborted', 'AbortError');
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(abort));

    await expect(getMe()).rejects.toBe(abort);
  });
});

describe('onSessionEnded', () => {
  afterEach(() => {
    setAccessToken(null);
    vi.unstubAllGlobals();
  });

  it('tells the listeners when an open session cannot be refreshed any more', async () => {
    stubBackend({ 'GET /auth/me': unauthorized, 'POST /auth/refresh': unauthorized });
    setAccessToken('expired-token');
    const listener = vi.fn();
    const unsubscribe: () => void = onSessionEnded(listener);

    await getMe().catch(() => undefined);

    expect(listener).toHaveBeenCalledTimes(1);
    unsubscribe();
  });

  it('tells no one when there was no session, as on page load', async () => {
    stubBackend({ 'POST /auth/refresh': unauthorized });
    const listener = vi.fn();
    const unsubscribe: () => void = onSessionEnded(listener);

    await expect(refreshAccessToken()).resolves.toBe(false);

    expect(listener).not.toHaveBeenCalled();
    unsubscribe();
  });

  it('stops telling a listener once it has unsubscribed', async () => {
    stubBackend({ 'POST /auth/refresh': unauthorized });
    setAccessToken('expired-token');
    const listener = vi.fn();
    onSessionEnded(listener)();

    await refreshAccessToken();

    expect(listener).not.toHaveBeenCalled();
  });
});
