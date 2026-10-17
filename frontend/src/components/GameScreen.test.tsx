import { fireEvent, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { CurrentGame, OwnPlacement, Room } from '../api/rooms';
import { aliceRoom, aliceRoomInGame, lousRoom } from '../test/fixtures/rooms';
import { renderRoomPage } from '../test/renderRoomPage';
import { calledRoutes, errorResponse, stubBackend } from '../test/stubBackend';

const game: CurrentGame = aliceRoomInGame.game as CurrentGame;
const [tierS, tierA]: CurrentGame['tiers'] = game.tiers;
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

  describe('during the final cooldown', () => {
    const barbecue = {
      id: '7c1d2e3f-0000-4000-8000-000000000002',
      text: 'Barbecue',
      image_url: null,
    };
    const paprikaPut = `PUT /rooms/K7P2QX/game/placements/${game.current_item.id}`;

    // Alice a placé Paprika puis Chorizo en S, et a manqué Barbecue
    function inCooldown(roomChanges: Partial<Room> = {}): Room {
      return inGame(
        {
          status: 'cooldown',
          cooldown_ends_at: new Date(Date.now() + 60_000).toISOString(),
          own_placements: [paprikaInS, chorizoInS],
          missed_items: [barbecue],
        },
        roomChanges,
      );
    }

    it('shows the banner, the final board and the missed items', async () => {
      stubBackend({ 'GET /rooms/K7P2QX': () => Response.json(inCooldown()) });
      renderRoomPage();

      expect(await screen.findByRole('heading', { name: 'Cooldown final' })).toBeInTheDocument();
      expect(screen.getByRole('timer', { name: 'Fin du cooldown' })).toBeInTheDocument();
      // Le glisser-déposer a sa propre zone d'annonces (status) : le texte du bandeau suffit
      expect(
        screen.getByText("Déplacez n'importe quelle tuile. Placez vos items manqués avant la fin."),
      ).toBeInTheDocument();
      const tierRow: HTMLElement = screen.getByRole('list', { name: 'S' });
      expect(within(tierRow).getByText('Paprika')).toBeInTheDocument();
      expect(within(tierRow).getByText('Chorizo')).toBeInTheDocument();
      const missed: HTMLElement | null = screen
        .getByRole('heading', { name: 'Items manqués' })
        .closest('section');
      if (missed === null) throw new Error('No missed items');
      expect(within(missed).getByText('Barbecue')).toBeInTheDocument();
      expect(within(missed).getByText('Absent')).toBeInTheDocument();
    });

    it('moves any tile with the arrow buttons', async () => {
      const bodies: unknown[] = [];
      stubBackend({
        'GET /rooms/K7P2QX': () => Response.json(inCooldown()),
        [paprikaPut]: async (request) => {
          bodies.push(await request.json());
          return Response.json(inCooldown());
        },
      });
      renderRoomPage();

      fireEvent.click(
        await screen.findByRole('button', { name: 'Descendre Paprika au tier du dessous' }),
      );
      await vi.waitFor(() => expect(bodies).toHaveLength(1));
      fireEvent.click(screen.getByRole('button', { name: 'Reculer Paprika dans son tier' }));

      await vi.waitFor(() =>
        expect(bodies).toEqual([
          { tier_id: tierA.id, position: 0 },
          { tier_id: tierS.id, position: 1 },
        ]),
      );
      // S est le premier tier : rien au-dessus
      expect(
        screen.getByRole('button', { name: 'Monter Paprika au tier du dessus' }),
      ).toBeDisabled();
    });

    it('places a missed item at the end of the chosen tier', async () => {
      let body: unknown;
      stubBackend({
        'GET /rooms/K7P2QX': () => Response.json(inCooldown()),
        [`PUT /rooms/K7P2QX/game/placements/${barbecue.id}`]: async (request) => {
          body = await request.json();
          return Response.json(inCooldown());
        },
      });
      renderRoomPage();

      fireEvent.change(await screen.findByLabelText('Tier où placer Barbecue'), {
        target: { value: tierA.id },
      });
      fireEvent.click(
        screen.getByRole('button', { name: 'Placer Barbecue à la fin du tier choisi' }),
      );

      await vi.waitFor(() => expect(body).toEqual({ tier_id: tierA.id, position: 0 }));
    });

    it('lets the room admin end the cooldown after confirming', async () => {
      const fetchMock = stubBackend({
        'GET /rooms/K7P2QX': () => Response.json(inCooldown()),
        'POST /rooms/K7P2QX/game/end': () => Response.json(aliceRoom),
      });
      renderRoomPage();

      fireEvent.click(await screen.findByRole('button', { name: 'Terminer maintenant' }));
      const dialog: HTMLElement = screen.getByRole('dialog', { name: 'Terminer le cooldown ?' });
      expect(calledRoutes(fetchMock)).not.toContain('POST /rooms/K7P2QX/game/end');
      fireEvent.click(within(dialog).getByRole('button', { name: 'Terminer' }));

      await vi.waitFor(() =>
        expect(screen.queryByRole('heading', { name: 'Cooldown final' })).not.toBeInTheDocument(),
      );
      expect(calledRoutes(fetchMock)).toContain('POST /rooms/K7P2QX/game/end');
    });

    it('gives a player the final board without the end button', async () => {
      stubBackend({
        'GET /rooms/K7P2QX': () =>
          Response.json(
            inCooldown({
              is_admin: false,
              participants: aliceRoomInGame.participants.map((participant) => ({
                ...participant,
                is_you: !participant.is_admin,
              })),
            }),
          ),
      });
      renderRoomPage();

      expect(await screen.findByRole('heading', { name: 'Mon classement' })).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Terminer maintenant' })).not.toBeInTheDocument();
    });

    it('gives the room admin who does not play only the end button', async () => {
      stubBackend({
        'GET /rooms/K7P2QX': () =>
          Response.json(
            inCooldown({ settings: { ...aliceRoomInGame.settings, admin_plays: false } }),
          ),
      });
      renderRoomPage();

      expect(
        await screen.findByRole('button', { name: 'Terminer maintenant' }),
      ).toBeInTheDocument();
      expect(screen.getByRole('status')).toHaveTextContent(
        'Les participants finalisent leur classement.',
      );
      expect(screen.queryByRole('heading', { name: 'Mon classement' })).not.toBeInTheDocument();
    });
  });
});
