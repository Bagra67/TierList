import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { CurrentGame, OwnPlacement, Room } from '../api/rooms';
import { aliceRoom, aliceRoomInGame, lousRoom } from '../test/fixtures/rooms';
import { latestSocket } from '../test/fakeWebSocket';
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
async function findPlacedList(): Promise<HTMLElement> {
  await screen.findByRole('heading', { name: /^Placé/ });
  return placedList();
}

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

    expect(await screen.findByText('Élément 1 sur 3')).toBeInTheDocument();
    expect(screen.getByText('Paprika')).toBeInTheDocument();
    // Bob, déconnecté, a placé : le compteur n'attend que les connectés (Alice)
    expect(screen.getByRole('heading', { name: 'Placé 0 / 1 connecté' })).toBeInTheDocument();
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

  it('shows the progress of the game', async () => {
    stubBackend({ 'GET /rooms/K7P2QX': () => Response.json(aliceRoomInGame) });
    renderRoomPage();

    const progress: HTMLElement = await screen.findByRole('progressbar', {
      name: 'Progression de la partie',
    });
    expect(progress).toHaveAttribute('aria-valuenow', '1');
    expect(progress).toHaveAttribute('aria-valuemax', '3');
    expect(progress).toHaveAttribute('aria-valuetext', 'Élément 1 sur 3');
  });

  it('turns the timer to the accent color in the last seconds', async () => {
    const endsAt: string = new Date(Date.now() + 3_000).toISOString();
    stubBackend({ 'GET /rooms/K7P2QX': () => Response.json(inGame({ ends_at: endsAt })) });
    renderRoomPage();

    const timer: HTMLElement = await screen.findByRole('timer', { name: 'Temps restant' });
    expect(timer).toHaveClass('bg-primary');
    expect(timer).not.toHaveClass('bg-spotlight');
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
      await screen.findByRole('button', { name: "Placer dans S : l'élément en cours, à la fin" }),
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

  it('shows a preview of the item while it is dragged', async () => {
    stubBackend({ 'GET /rooms/K7P2QX': () => Response.json(aliceRoomInGame) });
    renderRoomPage();
    const handle: HTMLElement = await screen.findByRole('button', {
      name: 'Glisser dans un tier : Paprika',
    });
    expect(screen.getAllByText('Paprika')).toHaveLength(1);

    fireEvent.keyDown(handle, { code: 'Space', key: ' ' });
    // L'aperçu, une copie de l'item, suit le glisser
    await waitFor(() => expect(screen.getAllByText('Paprika')).toHaveLength(2));

    fireEvent.keyDown(handle, { code: 'Escape', key: 'Escape' });
    await waitFor(() => expect(screen.getAllByText('Paprika')).toHaveLength(1));
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
      await screen.findByRole('button', { name: "Placer dans S : l'élément en cours, à la fin" }),
    );

    expect(await screen.findByRole('alert')).toHaveTextContent(
      "Cet élément n'est plus l'élément en cours : le tour est passé.",
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
    expect(screen.getByRole('region', { name: "Commandes de l'hôte" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Élément suivant' }));

    expect(await screen.findByText('Élément 2 sur 3')).toBeInTheDocument();
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

    expect(await screen.findByRole('button', { name: 'Élément suivant' })).toBeInTheDocument();
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
    expect(screen.queryByRole('button', { name: 'Élément suivant' })).not.toBeInTheDocument();
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
    expect(screen.getByText('Élément 1 sur 3')).toBeInTheDocument();
    expect(within(placedList()).getByText('Lou (vous)')).toBeInTheDocument();
    expect(calledRoutes(fetchMock)).not.toContain('GET /rooms/K7P2QX');
  });

  it('marks a participant as placed when the event arrives', async () => {
    stubBackend({ 'GET /rooms/K7P2QX': () => Response.json(aliceRoomInGame) });
    renderRoomPage();
    expect(await within(await findPlacedList()).findByText('Bob')).toBeInTheDocument();

    latestSocket().receive({
      type: 'participant.placed',
      room_version: aliceRoomInGame.version + 1,
      data: { participant_id: bobId, round_number: 1 },
    });

    await vi.waitFor(() =>
      expect(within(placedList()).getByText('Bob').parentElement).toHaveTextContent('a placé'),
    );
  });

  it('ignores an answer older than the room already shown', async () => {
    const barbecue = {
      id: '7c1d2e3f-0000-4000-8000-000000000002',
      text: 'Barbecue',
      image_url: null,
    };
    stubBackend({
      'GET /rooms/K7P2QX': () => Response.json(inGame({ round_number: 2, current_item: barbecue })),
      // Le tour 2 a commencé entre-temps : cette réponse du tour 1 arrive trop tard
      [`PUT /rooms/K7P2QX/game/placements/${barbecue.id}`]: () =>
        Response.json(inGame({ own_placements: [paprikaInS] })),
    });
    renderRoomPage();

    fireEvent.click(
      await screen.findByRole('button', { name: "Placer dans S : l'élément en cours, à la fin" }),
    );

    await vi.waitFor(() => expect(screen.getByText('Élément 2 sur 3')).toBeInTheDocument());
    expect(screen.queryByText('Élément 1 sur 3')).not.toBeInTheDocument();
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

      expect(await screen.findByRole('heading', { name: 'Retouches finales' })).toBeInTheDocument();
      expect(screen.getByRole('timer', { name: 'Fin des retouches' })).toBeInTheDocument();
      // Le glisser-déposer a sa propre zone d'annonces (status) : le texte du bandeau suffit
      expect(
        screen.getByText(
          "Déplacez n'importe quelle tuile. Placez vos éléments manqués avant la fin.",
        ),
      ).toBeInTheDocument();
      const tierRow: HTMLElement = screen.getByRole('list', { name: 'S' });
      expect(within(tierRow).getByText('Paprika')).toBeInTheDocument();
      expect(within(tierRow).getByText('Chorizo')).toBeInTheDocument();
      const missed: HTMLElement | null = screen
        .getByRole('heading', { name: 'Éléments manqués' })
        .closest('section');
      if (missed === null) throw new Error('No missed items');
      expect(within(missed).getByText('Barbecue')).toBeInTheDocument();
      expect(within(missed).getByText('Absent')).toBeInTheDocument();
    });

    it('shows a preview of a tile dragged on the final board', async () => {
      stubBackend({ 'GET /rooms/K7P2QX': () => Response.json(inCooldown()) });
      renderRoomPage();
      const chorizo: HTMLElement = await screen.findByRole('button', { name: 'Choisir Chorizo' });
      expect(screen.getAllByText('Chorizo')).toHaveLength(1);

      fireEvent.keyDown(chorizo, { code: 'Space', key: ' ' });
      await waitFor(() => expect(screen.getAllByText('Chorizo')).toHaveLength(2));

      fireEvent.keyDown(chorizo, { code: 'Escape', key: 'Escape' });
      await waitFor(() => expect(screen.getAllByText('Chorizo')).toHaveLength(1));
    });

    it('moves a chosen tile to the end of a tier', async () => {
      const bodies: unknown[] = [];
      stubBackend({
        'GET /rooms/K7P2QX': () => Response.json(inCooldown()),
        [paprikaPut]: async (request) => {
          bodies.push(await request.json());
          return Response.json(inCooldown());
        },
      });
      renderRoomPage();

      // Rien n'est choisi : pas de « Déplacer ici »
      expect(await screen.findByRole('button', { name: 'Choisir Paprika' })).toHaveAttribute(
        'aria-pressed',
        'false',
      );
      expect(screen.queryByRole('button', { name: /^Déplacer Paprika/ })).not.toBeInTheDocument();

      fireEvent.click(screen.getByRole('button', { name: 'Choisir Paprika' }));
      expect(screen.getByRole('button', { name: 'Choisir Paprika' })).toHaveAttribute(
        'aria-pressed',
        'true',
      );
      expect(screen.getByText('Tuile choisie : Paprika')).toBeInTheDocument();
      fireEvent.click(screen.getByRole('button', { name: 'Déplacer Paprika à la fin de A' }));

      await vi.waitFor(() => expect(bodies).toEqual([{ tier_id: tierA.id, position: 0 }]));
      // Une fois déplacée, la tuile n'est plus choisie
      expect(screen.queryByText('Tuile choisie : Paprika')).not.toBeInTheDocument();
    });

    it('cancels the choice of a tile', async () => {
      stubBackend({ 'GET /rooms/K7P2QX': () => Response.json(inCooldown()) });
      renderRoomPage();

      fireEvent.click(await screen.findByRole('button', { name: 'Choisir Chorizo' }));
      expect(screen.getAllByRole('button', { name: /^Déplacer Chorizo à la fin de/ })).toHaveLength(
        game.tiers.length,
      );
      fireEvent.click(screen.getByRole('button', { name: 'Annuler le choix' }));

      expect(screen.queryByRole('button', { name: /^Déplacer Chorizo/ })).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Choisir Chorizo' })).toHaveAttribute(
        'aria-pressed',
        'false',
      );
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

      fireEvent.click(await screen.findByRole('button', { name: 'Choisir Barbecue' }));
      fireEvent.click(screen.getByRole('button', { name: 'Déplacer Barbecue à la fin de A' }));

      await vi.waitFor(() => expect(body).toEqual({ tier_id: tierA.id, position: 0 }));
    });

    it('lets the room admin end the cooldown after confirming', async () => {
      const fetchMock = stubBackend({
        'GET /rooms/K7P2QX': () => Response.json(inCooldown()),
        // La partie close incrémente la version de la salle
        'POST /rooms/K7P2QX/game/end': () =>
          Response.json({ ...aliceRoom, version: aliceRoomInGame.version + 1 }),
      });
      renderRoomPage();

      fireEvent.click(await screen.findByRole('button', { name: 'Terminer maintenant' }));
      const dialog: HTMLElement = screen.getByRole('dialog', { name: 'Terminer les retouches ?' });
      expect(calledRoutes(fetchMock)).not.toContain('POST /rooms/K7P2QX/game/end');
      fireEvent.click(within(dialog).getByRole('button', { name: 'Terminer' }));

      await vi.waitFor(() =>
        expect(
          screen.queryByRole('heading', { name: 'Retouches finales' }),
        ).not.toBeInTheDocument(),
      );
      expect(calledRoutes(fetchMock)).toContain('POST /rooms/K7P2QX/game/end');
      // Le focus revient au lobby, au lieu de se perdre avec l'écran du cooldown
      expect(screen.getByRole('heading', { name: 'Salle K7P2QX' })).toHaveFocus();
    });

    it('sends nothing when the end is cancelled, and says why it failed', async () => {
      const fetchMock = stubBackend({
        'GET /rooms/K7P2QX': () => Response.json(inCooldown()),
        'POST /rooms/K7P2QX/game/end': () => errorResponse(409, 'cooldown_not_in_progress'),
      });
      renderRoomPage();

      fireEvent.click(await screen.findByRole('button', { name: 'Terminer maintenant' }));
      fireEvent.click(screen.getByRole('button', { name: 'Annuler' }));
      expect(calledRoutes(fetchMock)).not.toContain('POST /rooms/K7P2QX/game/end');

      fireEvent.click(screen.getByRole('button', { name: 'Terminer maintenant' }));
      const dialog: HTMLElement = screen.getByRole('dialog', { name: 'Terminer les retouches ?' });
      fireEvent.click(within(dialog).getByRole('button', { name: 'Terminer' }));

      expect(await within(dialog).findByRole('alert')).toHaveTextContent(
        'Les retouches finales ne sont pas en cours.',
      );
    });

    it('keeps the keyboard focus on the moved tile', async () => {
      let body: unknown;
      let answer: (room: Room) => void = () => {};
      stubBackend({
        'GET /rooms/K7P2QX': () => Response.json(inCooldown()),
        [paprikaPut]: async (request) => {
          body = await request.json();
          return new Promise<Response>((resolve) => {
            answer = (room: Room) => resolve(Response.json(room));
          });
        },
      });
      renderRoomPage();

      fireEvent.click(await screen.findByRole('button', { name: 'Choisir Paprika' }));
      // Déjà en S : « Déplacer ici » la met à la dernière place du tier
      fireEvent.click(screen.getByRole('button', { name: 'Déplacer Paprika à la fin de S' }));
      await vi.waitFor(() => expect(body).toEqual({ tier_id: tierS.id, position: 1 }));
      const cooldown: Room = inCooldown();
      answer({
        ...cooldown,
        game: {
          ...(cooldown.game as CurrentGame),
          own_placements: [
            { ...chorizoInS, position: 0 },
            { ...paprikaInS, position: 1 },
          ],
        },
      });

      const paprika: HTMLElement = await screen.findByRole('button', { name: 'Choisir Paprika' });
      await vi.waitFor(() => expect(paprika).toHaveFocus());
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
      expect(screen.getByText('Les participants finalisent leur classement.')).toBeInTheDocument();
      expect(screen.queryByRole('heading', { name: 'Mon classement' })).not.toBeInTheDocument();
    });
  });
});
