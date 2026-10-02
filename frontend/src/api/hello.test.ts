import { afterEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from './client';
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
      vi.fn().mockResolvedValue(Response.json({ detail: 'boom' }, { status: 500 })),
    );

    const error = await getHello().catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 500, body: { detail: 'boom' } });
  });
});
