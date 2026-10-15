import { QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react';
import { createElement, type ReactNode } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { roomQueryKey } from '../constants/rooms';
import { FakeWebSocket, latestSocket } from '../test/fakeWebSocket';
import { aliceRoom } from '../test/rooms';
import { stubBackend, tokenResponse, unauthorized } from '../test/stubBackend';
import { setAccessToken } from './client';
import { createQueryClient } from './queryClient';
import type { Room, RoomViewer } from './rooms';
import { useRoomEvents } from './roomChannel';

const bobId: string = aliceRoom.participants[1].id;

// Canal de la salle d'Alice (version 3 en cache), suivi par ce lecteur
function followRoom(viewer: RoomViewer = 'account') {
  const queryClient = createQueryClient({ queries: { retry: false } });
  queryClient.setQueryData(roomQueryKey(aliceRoom.code), aliceRoom);
  const hook = renderHook(() => useRoomEvents(aliceRoom.code.toLowerCase(), viewer, true), {
    wrapper: ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client: queryClient }, children),
  });
  return { queryClient, ...hook };
}

function cachedRoom(queryClient: ReturnType<typeof createQueryClient>): Room | undefined {
  return queryClient.getQueryData<Room>(roomQueryKey(aliceRoom.code));
}

function isInvalidated(queryClient: ReturnType<typeof createQueryClient>): boolean {
  return queryClient.getQueryState(roomQueryKey(aliceRoom.code))?.isInvalidated ?? false;
}

function presence(roomVersion: number, connected: boolean): object {
  return {
    type: 'participant.presence',
    room_version: roomVersion,
    data: { participant_id: bobId, connected },
  };
}

describe('useRoomEvents', () => {
  afterEach(() => {
    setAccessToken(null);
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('opens the room channel and authenticates with the access token', async () => {
    setAccessToken('alice-token');
    followRoom('account');

    const socket: FakeWebSocket = latestSocket();
    socket.acceptConnection();

    expect(socket.url).toBe(`ws://${window.location.host}/api/rooms/K7P2QX/ws`);
    await waitFor(() =>
      expect(socket.sentMessages()).toEqual([{ type: 'auth', access_token: 'alice-token' }]),
    );
  });

  it('lets the guest cookie authenticate a guest', async () => {
    followRoom('guest');

    latestSocket().acceptConnection();

    await waitFor(() =>
      expect(latestSocket().sentMessages()).toEqual([{ type: 'auth', access_token: null }]),
    );
  });

  it('answers the heartbeat', () => {
    followRoom();

    latestSocket().receive({ type: 'ping' });

    expect(latestSocket().sentMessages()).toEqual([{ type: 'pong' }]);
  });

  it('updates the presence in the cache without reading the room again', () => {
    const { queryClient } = followRoom();

    latestSocket().receive(presence(4, true));

    const room: Room | undefined = cachedRoom(queryClient);
    expect(room?.version).toBe(4);
    expect(room?.participants[1].connected).toBe(true);
    expect(isInvalidated(queryClient)).toBe(false);
  });

  it('reads the room again when someone joins', () => {
    const { queryClient } = followRoom();

    latestSocket().receive({
      type: 'participant.joined',
      room_version: 4,
      data: { participant_id: '9a1b2c3d-0000-4000-8000-000000000009' },
    });

    expect(isInvalidated(queryClient)).toBe(true);
  });

  it('reads the room again after a missed event', () => {
    const { queryClient } = followRoom();

    // Version 5 alors que la salle en cache est en version 3 : la 4 a été manquée
    latestSocket().receive(presence(5, true));

    expect(isInvalidated(queryClient)).toBe(true);
    expect(cachedRoom(queryClient)?.participants[1].connected).toBe(false);
  });

  it('ignores an event already included in the room', () => {
    const { queryClient } = followRoom();

    latestSocket().receive(presence(3, true));

    expect(isInvalidated(queryClient)).toBe(false);
    expect(cachedRoom(queryClient)?.participants[1].connected).toBe(false);
  });

  it('reconnects after an unexpected close, but not after room_not_found', () => {
    vi.useFakeTimers();
    followRoom();

    latestSocket().closeFromServer(1006);
    vi.advanceTimersByTime(500);
    expect(FakeWebSocket.instances).toHaveLength(2);

    latestSocket().closeFromServer(4404);
    vi.advanceTimersByTime(10_000);
    expect(FakeWebSocket.instances).toHaveLength(2);
  });

  it('closes the channel when the page leaves the room', () => {
    vi.useFakeTimers();
    const { unmount } = followRoom();
    const socket: FakeWebSocket = latestSocket();

    unmount();
    vi.advanceTimersByTime(10_000);

    expect(socket.readyState).toBe(FakeWebSocket.CLOSED);
    expect(FakeWebSocket.instances).toHaveLength(1);
  });

  it('retries once with a refreshed token when the session token has expired', async () => {
    setAccessToken('expired-token');
    stubBackend({ 'POST /auth/refresh': tokenResponse('fresh-token') });
    followRoom('account');

    latestSocket().closeFromServer(4401);

    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(2));
    latestSocket().acceptConnection();
    await waitFor(() =>
      expect(latestSocket().sentMessages()).toEqual([
        { type: 'auth', access_token: 'fresh-token' },
      ]),
    );
    // Refusé une seconde fois d'affilée : la session est vraiment finie
    latestSocket().closeFromServer(4401);
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(FakeWebSocket.instances).toHaveLength(2);
  });

  it('stops when the session cannot be refreshed', async () => {
    setAccessToken('expired-token');
    stubBackend({ 'POST /auth/refresh': unauthorized });
    followRoom('account');

    latestSocket().closeFromServer(4401);
    await new Promise((resolve) => setTimeout(resolve, 50));

    expect(FakeWebSocket.instances).toHaveLength(1);
  });

  it('gives up and says so after several failed openings', () => {
    vi.useFakeTimers();
    const { result } = followRoom();

    for (let failure = 1; failure < 5; failure += 1) {
      act(() => {
        latestSocket().closeFromServer(1006);
        vi.advanceTimersByTime(10_000);
      });
    }
    expect(result.current.unavailable).toBe(false);
    act(() => {
      latestSocket().closeFromServer(1006);
      vi.advanceTimersByTime(10_000);
    });

    expect(FakeWebSocket.instances).toHaveLength(5);
    expect(result.current.unavailable).toBe(true);
  });

  it('keeps retrying after a connection that was open', () => {
    vi.useFakeTimers();
    // Invité : l'ouverture n'a pas besoin de rafraîchir un token
    followRoom('guest');

    for (let drop = 0; drop < 6; drop += 1) {
      latestSocket().acceptConnection();
      latestSocket().closeFromServer(1006);
      vi.advanceTimersByTime(10_000);
    }

    expect(FakeWebSocket.instances).toHaveLength(7);
  });
});
