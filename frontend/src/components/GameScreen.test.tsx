import { fireEvent, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { CurrentGame, OwnPlacement, Room } from '../api/rooms';
import { aliceRoomInGame, lousRoom } from '../test/fixtures/rooms';
import { renderRoomPage } from '../test/renderRoomPage';
import { calledRoutes, errorResponse, stubBackend } from '../test/stubBackend';

const game: CurrentGame = aliceRoomInGame.game as CurrentGame;
const [tierS]: CurrentGame['tiers'] = game.tiers;
const bobId: string = aliceRoomInGame.participants[1].id;

// La salle d'Alice pendant la partie, avec ces changements de la partie
function inGame(changes: Partial<CurrentGame>, roomChanges: Partial<Room> = {}): Room {
  return { ...aliceRoomInGame, ...roomChanges, game: { ...game, ...changes } };
}

// Alice a placé l'item en cours, Paprika, en tête de S
const paprikaInS: OwnPlacement = { item: game.current_item, tier_id: tierS.id, position: 0 };
const chorizoInS: OwnPlacement = {
  item: { id: '7c1d2e3f-0000-4000-8000-000000000009', text: 'Chorizo', image_url: null },
  tier_id: tierS.id,
  position: 1,
};

// La liste « qui a placé » : le lobby, en dessous, nomme aussi les participants
function placedList(): HTMLElement {
  const section: HTMLElement | null = screen
    .getByRole('heading', { name: /^Placé/ })
    .closest('section');
  if (section === null) throw new Error('No placed list');
  return section;
}

describe('GameScreen', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('shows the current item, its progress and who has placed it', async () => {
    stubBackend({
      'GET /rooms/K7P2QX': () => Response.json(inGame({ placed_participant_ids: [bobId] })),
    });
    renderRoomPage();

    expect(await screen.findByText('Item 1 sur 3')).toBeInTheDocument();
    expect(screen.getByText('Paprika')).toBeInTheDocument();
    // Bob, déconnecté, a placé : le compteur n'attend que les connectés (Alice)
    expect(screen.getByRole('heading', { name: 'Placé 0 / 1 connectés' })).toBeInTheDocument();
    expect(within(placedList()).getByText('Alice (vous)').parentElement).toHaveTextContent(
      'en attente',
    );
    expect(within(placedList()).getByText('Bob').parentElement).toHaveTextContent('a placé');
  });

  it('counts down to the end of the round timer', async () => {
    const endsAt: string = new Date(Date.now() + 75_000).toISOString();
    stubBackend({ 'GET /rooms/K7P2QX': () => Response.json(inGame({ ends_at: endsAt })) });
    renderRoomPage();

    expect(await screen.findByRole('timer', { name: 'Temps restant' })).toHaveTextContent(
      /^1:1[45]$/,
    );
  });

  it('places the current item at the end of a tier with its button', async () => {
    let body: unknown;
    const fetchMock = stubBackend({
      'GET /rooms/K7P2QX': () => Response.json(aliceRoomInGame),
      [`PUT /rooms/K7P2QX/game/placements/${game.current_item.id}`]: async (request) => {
        body = await request.json();
        return Response.json(inGame({ own_placements: [paprikaInS] }));
      },
    });
    renderRoomPage();

    fireEvent.click(
      await screen.findByRole('button', { name: "Placer l'item en cours à la fin de S" }),
    );

    const tierRow: HTMLElement = await screen.findByRole('list', { name: 'S' });
    expect(await within(tierRow).findByText('Paprika')).toBeInTheDocument();
    expect(body).toEqual({ tier_id: tierS.id, position: 0 });
    expect(calledRoutes(fetchMock)).toContain(
      `PUT /rooms/K7P2QX/game/placements/${game.current_item.id}`,
    );
    // Seul dans son tier : il ne peut ni avancer ni reculer
    expect(screen.getByRole('button', { name: 'Avancer Paprika dans son tier' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Reculer Paprika dans son tier' })).toBeDisabled();
  });

  it('moves the placed item one position later in its tier', async () => {
    let body: unknown;
    stubBackend({
      'GET /rooms/K7P2QX': () =>
        Response.json(inGame({ own_placements: [paprikaInS, chorizoInS] })),
      [`PUT /rooms/K7P2QX/game/placements/${game.current_item.id}`]: async (request) => {
        body = await request.json();
        return Response.json(inGame({ own_placements: [paprikaInS, chorizoInS] }));
      },
    });
    renderRoomPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Reculer Paprika dans son tier' }));

    await vi.waitFor(() => expect(body).toEqual({ tier_id: tierS.id, position: 1 }));
  });

  it('says why the item could not be placed', async () => {
    stubBackend({
      'GET /rooms/K7P2QX': () => Response.json(aliceRoomInGame),
      [`PUT /rooms/K7P2QX/game/placements/${game.current_item.id}`]: () =>
        errorResponse(409, 'item_not_current'),
    });
    renderRoomPage();

    fireEvent.click(
      await screen.findByRole('button', { name: "Placer l'item en cours à la fin de S" }),
    );

    expect(await screen.findByRole('alert')).toHaveTextContent(
      "Cet item n'est plus l'item en cours : le tour est passé.",
    );
  });

  it('lets the room admin move on to the next item', async () => {
    const nextItem = {
      id: '7c1d2e3f-0000-4000-8000-000000000002',
      text: 'Barbecue',
      image_url: null,
    };
    const fetchMock = stubBackend({
      'GET /rooms/K7P2QX': () => Response.json(aliceRoomInGame),
      'POST /rooms/K7P2QX/game/next': () =>
        Response.json(inGame({ round_number: 2, current_item: nextItem })),
    });
    renderRoomPage();

    expect(await screen.findByText('Passage automatique : désactivé')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Item suivant' }));

    expect(await screen.findByText('Item 2 sur 3')).toBeInTheDocument();
    expect(screen.getByText('Barbecue')).toBeInTheDocument();
    expect(calledRoutes(fetchMock)).toContain('POST /rooms/K7P2QX/game/next');
  });

  it('gives the room admin who does not play only the controls', async () => {
    stubBackend({
      'GET /rooms/K7P2QX': () =>
        Response.json(
          inGame({}, { settings: { ...aliceRoomInGame.settings, admin_plays: false } }),
        ),
    });
    renderRoomPage();

    expect(await screen.findByRole('button', { name: 'Item suivant' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Mon classement' })).not.toBeInTheDocument();
    // Il n'est pas attendu : seul Bob compte
    expect(within(placedList()).queryByText('Alice (vous)')).not.toBeInTheDocument();
    expect(within(placedList()).getByText('Bob')).toBeInTheDocument();
  });

  it('gives a player their board without the controls', async () => {
    stubBackend({
      'GET /rooms/K7P2QX': () =>
        Response.json(
          inGame(
            {},
            {
              is_admin: false,
              participants: aliceRoomInGame.participants.map((participant) => ({
                ...participant,
                is_you: !participant.is_admin,
              })),
            },
          ),
        ),
    });
    renderRoomPage();

    expect(await screen.findByRole('heading', { name: 'Mon classement' })).toBeInTheDocument();
    expect(screen.getByText('Bob (vous)')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Item suivant' })).not.toBeInTheDocument();
  });

  it('brings a guest back to their board from the personal link during a game', async () => {
    const fetchMock = stubBackend({
      'POST /rooms/K7P2QX/guest-session': () =>
        Response.json({
          ...lousRoom,
          status: 'playing',
          game: { ...game, own_placements: [paprikaInS] },
        }),
    });
    renderRoomPage('K7P2QX#guest=lou-token');

    const tierRow: HTMLElement = await screen.findByRole('list', { name: 'S' });
    expect(within(tierRow).getByText('Paprika')).toBeInTheDocument();
    expect(screen.getByText('Item 1 sur 3')).toBeInTheDocument();
    expect(within(placedList()).getByText('Lou (vous)')).toBeInTheDocument();
    expect(calledRoutes(fetchMock)).not.toContain('GET /rooms/K7P2QX');
  });

  it('shows the final cooldown after the last item', async () => {
    const cooldownEndsAt: string = new Date(Date.now() + 60_000).toISOString();
    stubBackend({
      'GET /rooms/K7P2QX': () =>
        Response.json(inGame({ status: 'cooldown', cooldown_ends_at: cooldownEndsAt })),
    });
    renderRoomPage();

    expect(await screen.findByRole('status')).toHaveTextContent(
      'Le dernier item est passé : le cooldown final est en cours.',
    );
    expect(screen.getByRole('timer', { name: 'Fin du cooldown' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Mon classement' })).not.toBeInTheDocument();
  });
});
