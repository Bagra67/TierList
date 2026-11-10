import { act, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { CurrentGame, Room } from '../api/rooms';
import { aliceRoomInGame } from '../test/fixtures/rooms';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { CooldownBoard } from './CooldownBoard';
import { CooldownStage } from './CooldownStage';

vi.mock('./CooldownBoard', async (importOriginal) => {
  const original = await importOriginal<typeof import('./CooldownBoard')>();
  return { CooldownBoard: vi.fn(original.CooldownBoard) };
});

function roomInCooldown(): { room: Room; game: CurrentGame } {
  const game: CurrentGame = {
    ...(aliceRoomInGame.game as CurrentGame),
    status: 'cooldown',
    cooldown_ends_at: new Date(Date.now() + 60_000).toISOString(),
  };
  return { room: { ...aliceRoomInGame, game }, game };
}

describe('CooldownStage', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('counts down each second without drawing the final board again', () => {
    vi.useFakeTimers();
    const { room, game } = roomInCooldown();
    renderWithQueryClient(
      <CooldownStage room={room} game={game} readerPlaces endCooldown={null} />,
    );
    const rendersAtStart: number = vi.mocked(CooldownBoard).mock.calls.length;

    act(() => vi.advanceTimersByTime(3_000));

    expect(screen.getByRole('timer', { name: 'Fin des retouches' })).toHaveTextContent('0:57');
    expect(vi.mocked(CooldownBoard).mock.calls).toHaveLength(rendersAtStart);
  });
});
