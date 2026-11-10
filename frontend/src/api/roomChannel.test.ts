import { QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react';
import { createElement, type ReactNode } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { roomQueryKey } from '../constants/rooms';
import { FakeWebSocket, latestSocket } from '../test/fakeWebSocket';
import { aliceRoom, aliceRoomInGame } from '../test/fixtures/rooms';
import { stubBackend, tokenResponse, unauthorized } from '../test/stubBackend';
import { setAccessToken } from './client';
import { createQueryClient } from './queryClient';
import type { Room, RoomViewer } from './rooms';
import { type RemovalReason, useRoomEvents } from './roomChannel';

const bobId: string = aliceRoom.participants[1].id;

function followRoom(viewer: RoomViewer = 'account') {
  const queryClient = createQueryClient({ queries: { retry: false } });
  queryClient.setQueryData(roomQueryKey(aliceRoom.code), aliceRoom);
  const stableOnRemoved = vi.fn<(reason: RemovalReason) => void>();
  const hook = renderHook(
    () => useRoomEvents(aliceRoom.code.toLowerCase(), viewer, true, stableOnRemoved),
    {
      wrapper: ({ children }: { children: ReactNode }) =>
        createElement(QueryClientProvider, { client: queryClient }, children),
    },
  );
  return { queryClient, onRemoved: stableOnRemoved, ...hook };
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

  it('adds who placed the current item to the cache without reading the room again', () => {
    const { queryClient } = followRoom();
    queryClient.setQueryData(roomQueryKey(aliceRoom.code), aliceRoomInGame);

    latestSocket().receive({
      type: 'participant.placed',
      room_version: aliceRoomInGame.version + 1,
      data: { participant_id: bobId, round_number: 1 },
    });

    const room: Room | undefined = cachedRoom(queryClient);
    expect(room?.version).toBe(aliceRoomInGame.version + 1);
    expect(room?.game?.placed_participant_ids).toEqual([bobId]);
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

  it.each(['round.started', 'cooldown.started', 'game.closed'])(
    'reads the room again on %s',
    (type: string) => {
      const { queryClient } = followRoom();

      latestSocket().receive({ type, room_version: 4, data: {} });

      expect(isInvalidated(queryClient)).toBe(true);
    },
  );

  it('removes a participant from the cache without reading the room again', () => {
    const { queryClient } = followRoom();

    latestSocket().receive({
      type: 'participant.removed',
      room_version: 4,
      data: { participant_id: bobId },
    });

    const room: Room | undefined = cachedRoom(queryClient);
    expect(room?.version).toBe(4);
    expect(room?.participants.map((participant) => participant.display_name)).toEqual(['Alice']);
    expect(isInvalidated(queryClient)).toBe(false);
  });

  it.each<[number, RemovalReason]>([
    [4410, 'removed'],
    [4411, 'banned'],
    [4412, 'closed'],
  ])('tells the page and stops after the close code %i', (closeCode, reason) => {
    vi.useFakeTimers();
    const { onRemoved } = followRoom();

    latestSocket().closeFromServer(closeCode);
    vi.advanceTimersByTime(10_000);

    expect(onRemoved).toHaveBeenCalledExactlyOnceWith(reason);
    expect(FakeWebSocket.instances).toHaveLength(1);
  });

  it('reads the room again after a missed event', () => {
    const { queryClient } = followRoom();

    const versionAfterAGap: number = aliceRoom.version + 2;
    latestSocket().receive(presence(versionAfterAGap, true));

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

  it('reconnects later when the token cannot be read after the opening', async () => {
    stubBackend({ 'POST /auth/refresh': () => Response.json({}, { status: 503 }) });
    followRoom('account');
    const socket: FakeWebSocket = latestSocket();

    socket.acceptConnection();

    await waitFor(() => expect(socket.readyState).toBe(FakeWebSocket.CLOSED));
    expect(socket.sentMessages()).toEqual([]);
    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(2), { timeout: 2_000 });
  });

  it('reconnects later when the expired token cannot be refreshed for now', async () => {
    setAccessToken('expired-token');
    stubBackend({ 'POST /auth/refresh': () => Response.json({}, { status: 503 }) });
    followRoom('account');

    latestSocket().closeFromServer(4401);

    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(2), { timeout: 2_000 });
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
    followRoom('guest');

    for (let drop = 0; drop < 6; drop += 1) {
      latestSocket().acceptConnection();
      latestSocket().closeFromServer(1006);
      vi.advanceTimersByTime(10_000);
    }

    expect(FakeWebSocket.instances).toHaveLength(7);
  });
});
