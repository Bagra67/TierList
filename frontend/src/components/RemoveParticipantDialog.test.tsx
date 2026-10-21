import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { Room } from '../api/rooms';
import { aliceRoom, lousRoom } from '../test/fixtures/rooms';
import { renderRoomPage } from '../test/renderRoomPage';
import { calledRoutes, errorResponse, stubBackend, type BackendMock } from '../test/stubBackend';

const bobId: string = aliceRoom.participants[1].id;

// Salle d'Alice, room admin, avec Bob et Lou (invité)
const roomWithLou: Room = { ...aliceRoom, participants: lousRoom.participants };

// Adresse de l'unique DELETE reçu par le faux backend, une fois envoyé
async function sentDeletion(fetchMock: BackendMock): Promise<URL> {
  const request: Request = await waitFor(() => {
    const deletion = fetchMock.mock.calls.find(([call]) => call.method === 'DELETE');
    if (deletion === undefined) throw new Error('No DELETE request yet');
    return deletion[0];
  });
  return new URL(request.url);
}

// Ouvre le lobby, puis le dialogue de retrait de ce participant
async function openRemoval(name: string, routes: Parameters<typeof stubBackend>[0] = {}) {
  const fetchMock: BackendMock = stubBackend({
    'GET /rooms/K7P2QX': () => Response.json(roomWithLou),
    ...routes,
  });
  renderRoomPage();
  fireEvent.click(await screen.findByRole('button', { name: `Retirer ${name}` }));
  const dialog: HTMLElement = screen.getByRole('dialog', { name: `Retirer ${name} ?` });
  return { fetchMock, dialog };
}

describe('RemoveParticipantDialog', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('removes a participant, who leaves the lobby', async () => {
    const { fetchMock, dialog } = await openRemoval('Bob', {
      [`DELETE /rooms/K7P2QX/participants/${bobId}`]: () =>
        Response.json({
          ...roomWithLou,
          participants: roomWithLou.participants.filter((participant) => participant.id !== bobId),
        }),
    });

    fireEvent.click(within(dialog).getByRole('button', { name: 'Retirer' }));

    await waitFor(() => expect(screen.queryByText('Bob')).not.toBeInTheDocument());
    expect((await sentDeletion(fetchMock)).searchParams.get('ban')).toBe('false');
  });

  it('bans a participant, who then appears among the banned', async () => {
    const { fetchMock, dialog } = await openRemoval('Bob', {
      [`DELETE /rooms/K7P2QX/participants/${bobId}`]: () =>
        Response.json({
          ...aliceRoom,
          participants: [aliceRoom.participants[0]],
          bans: [{ id: 'ban-bob', display_name: 'Bob', is_guest: false }],
        }),
    });

    fireEvent.click(
      within(dialog).getByLabelText('Bannir : ne pourra plus revenir dans cette salle'),
    );
    // Pas d'avertissement pour un compte : son bannissement est sûr
    expect(within(dialog).queryByText(/contourner/)).not.toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole('button', { name: 'Bannir' }));

    expect(await screen.findByRole('heading', { name: 'Bannis (1)' })).toBeInTheDocument();
    expect((await sentDeletion(fetchMock)).searchParams.get('ban')).toBe('true');
  });

  it('warns that a guest can get around a ban', async () => {
    const { dialog } = await openRemoval('Lou');

    fireEvent.click(
      within(dialog).getByLabelText('Bannir : ne pourra plus revenir dans cette salle'),
    );

    expect(within(dialog).getByText(/Un invité peut contourner le bannissement/)).toBeVisible();
  });

  it('sends nothing when cancelled', async () => {
    const { fetchMock, dialog } = await openRemoval('Bob');

    fireEvent.click(within(dialog).getByRole('button', { name: 'Annuler' }));

    expect(calledRoutes(fetchMock)).not.toContain(`DELETE /rooms/K7P2QX/participants/${bobId}`);
    expect(screen.getByText('Bob')).toBeInTheDocument();
  });

  it('shows the error', async () => {
    const { dialog } = await openRemoval('Bob', {
      [`DELETE /rooms/K7P2QX/participants/${bobId}`]: () =>
        errorResponse(404, 'participant_not_found'),
    });

    fireEvent.click(within(dialog).getByRole('button', { name: 'Retirer' }));

    expect(
      await within(dialog).findByText("Ce participant n'est plus dans la salle."),
    ).toBeInTheDocument();
  });

  it('is only offered to the room admin, never on their own row', async () => {
    stubBackend({ 'GET /rooms/K7P2QX': () => Response.json(roomWithLou) });
    renderRoomPage();

    await screen.findByRole('button', { name: 'Retirer Bob' });
    expect(screen.getByRole('button', { name: 'Retirer Lou' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Retirer Alice' })).not.toBeInTheDocument();
  });

  it('is not offered to a player', async () => {
    stubBackend({ 'GET /rooms/K7P2QX': () => Response.json({ ...roomWithLou, is_admin: false }) });
    renderRoomPage();

    await screen.findByText('Bob');
    expect(screen.queryByRole('button', { name: /^Retirer/ })).not.toBeInTheDocument();
  });
});
