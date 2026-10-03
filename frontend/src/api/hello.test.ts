import { afterEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '../errors/apiError';
import { getHello } from './hello';

describe('getHello', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('calls GET /api/hello and returns the JSON body', async () => {
    const fetchMock = vi.fn().mockResolvedValue(Response.json({ message: 'Hello World' }));
    vi.stubGlobal('fetch', fetchMock);

    await expect(getHello()).resolves.toEqual({ message: 'Hello World' });

    const request = fetchMock.mock.calls[0][0] as Request;
    expect(request.method).toBe('GET');
    expect(new URL(request.url).pathname).toBe('/api/hello');
  });

  it('throws an ApiError carrying the status when the backend fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          Response.json({ detail: 'boom', code: 'internal_error' }, { status: 500 }),
        ),
    );

    const error = await getHello().catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 500,
      code: 'internal_error',
      body: { detail: 'boom', code: 'internal_error' },
      message: 'boom',
    });
  });

  it('falls back to the HTTP status when the body is not an ErrorResponse', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('Bad Gateway', { status: 502 })));

    const error = await getHello().catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 502, message: 'HTTP 502' });
  });
});
