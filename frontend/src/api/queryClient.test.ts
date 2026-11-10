import type { ErrorEvent } from '@sentry/react';
import { afterEach, describe, expect, it, type MockInstance, vi } from 'vitest';

import { ApiError } from '../errors/apiError';
import { type CapturedSentryEvents, captureSentryEvents } from '../test/sentryEvents';
import { createQueryClient } from './queryClient';

async function failQuery(error: Error): Promise<void> {
  const queryClient = createQueryClient({ queries: { retry: false } });
  await queryClient
    .fetchQuery({
      queryKey: ['rooms', 'K7P2QX'],
      queryFn: () => Promise.reject(error),
    })
    .catch(() => undefined);
}

describe('createQueryClient', () => {
  let consoleError: MockInstance;

  afterEach(() => {
    consoleError.mockRestore();
  });

  it('does not log an expected client error, which the page already shows', async () => {
    consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

    await failQuery(new ApiError(404, { detail: 'Room not found', code: 'room_not_found' }));

    expect(consoleError).not.toHaveBeenCalled();
  });

  it('logs a server error or an unreachable backend', async () => {
    consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

    await failQuery(new ApiError(502, 'Bad Gateway'));
    await failQuery(new TypeError('Failed to fetch'));

    expect(consoleError).toHaveBeenCalledTimes(2);
    expect(consoleError).toHaveBeenCalledWith(
      'Échec de la requête ["rooms","K7P2QX"]',
      expect.any(ApiError),
    );
  });

  it('reports a server error to Sentry, but not a client error', async () => {
    consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    const captured: CapturedSentryEvents = captureSentryEvents();
    const events: ErrorEvent[] = captured.events;

    try {
      await failQuery(new ApiError(404, { detail: 'Room not found', code: 'room_not_found' }));
      await failQuery(new ApiError(502, 'Bad Gateway'));

      await vi.waitFor(() => expect(events).toHaveLength(1));
      expect(events[0].exception?.values?.[0]).toMatchObject({
        type: 'ApiError',
        value: 'HTTP 502',
      });
    } finally {
      await captured.stop();
    }
  });
});
