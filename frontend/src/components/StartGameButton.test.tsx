import { fireEvent, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { aliceRoom, aliceRoomInGame } from '../test/fixtures/rooms';
import { renderRoomPage } from '../test/renderRoomPage';
import { calledRoutes, errorResponse, stubBackend } from '../test/stubBackend';

describe('StartGameButton', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('starts the game and shows the first item', async () => {
    const fetchMock = stubBackend({
      'GET /rooms/K7P2QX': () => Response.json(aliceRoom),
      'POST /rooms/K7P2QX/game': () => Response.json(aliceRoomInGame, { status: 201 }),
    });
    renderRoomPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Lancer la partie' }));

    expect(await screen.findByText('Élément 1 sur 3')).toBeInTheDocument();
    expect(screen.getByText('Partie en cours')).toBeInTheDocument();
    expect(screen.getByText('Paprika')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Lancer la partie' })).not.toBeInTheDocument();
    expect(calledRoutes(fetchMock)).toContain('POST /rooms/K7P2QX/game');
  });

  it('says play again once the room has a past game, and starts the next game', async () => {
    const fetchMock = stubBackend({
      'GET /rooms/K7P2QX': () =>
        Response.json({
          ...aliceRoom,
          past_games: [
            { public_token: 'past-token', closed_at: '2026-10-17T18:30:00Z', player_count: 2 },
          ],
        }),
      'POST /rooms/K7P2QX/game': () => Response.json(aliceRoomInGame, { status: 201 }),
    });
    renderRoomPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Rejouer' }));

    expect(await screen.findByText('Élément 1 sur 3')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Lancer la partie' })).not.toBeInTheDocument();
    expect(calledRoutes(fetchMock)).toContain('POST /rooms/K7P2QX/game');
  });

  it('says why the game cannot start', async () => {
    stubBackend({
      'GET /rooms/K7P2QX': () => Response.json(aliceRoom),
      'POST /rooms/K7P2QX/game': () => errorResponse(409, 'no_placing_participant'),
    });
    renderRoomPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Lancer la partie' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Il faut au moins un participant qui place les éléments',
    );
  });

  it('is only offered to the room admin', async () => {
    stubBackend({ 'GET /rooms/K7P2QX': () => Response.json({ ...aliceRoom, is_admin: false }) });
    renderRoomPage();

    await screen.findByRole('heading', { name: 'Salle K7P2QX' });
    expect(screen.queryByRole('button', { name: 'Lancer la partie' })).not.toBeInTheDocument();
  });

  it('is not offered when the template of the room was purged', async () => {
    stubBackend({ 'GET /rooms/K7P2QX': () => Response.json({ ...aliceRoom, template: null }) });
    renderRoomPage();

    await screen.findByRole('heading', { name: 'Salle K7P2QX' });
    expect(screen.queryByRole('button', { name: 'Lancer la partie' })).not.toBeInTheDocument();
  });

  it('is not offered during a game', async () => {
    stubBackend({ 'GET /rooms/K7P2QX': () => Response.json(aliceRoomInGame) });
    renderRoomPage();

    await screen.findByText('Élément 1 sur 3');
    expect(screen.queryByRole('button', { name: 'Lancer la partie' })).not.toBeInTheDocument();
  });
});
