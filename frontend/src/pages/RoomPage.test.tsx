import { act, fireEvent, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, type MockInstance, vi } from 'vitest';

import type { Room } from '../api/rooms';
import { setAccessToken } from '../api/client';
import { latestSocket } from '../test/fakeWebSocket';
import { aliceRoom, renderRoomPage, settingsSummary, signedInSession } from '../test/rooms';
import { calledRoutes, errorResponse, stubBackend } from '../test/stubBackend';

type BackendMock = ReturnType<typeof stubBackend>;

// Presse-papiers simulé : jsdom n'en fournit pas
function stubClipboard(writeText: (text: string) => Promise<void>): void {
  Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true });
}

describe('RoomPage', () => {
  afterEach(() => {
    setAccessToken(null);
    vi.unstubAllGlobals();
    Reflect.deleteProperty(navigator, 'clipboard');
  });

  it('shows the code, the link, the participants and the settings', async () => {
    stubBackend({ 'GET /rooms/K7P2QX': () => Response.json(aliceRoom) });

    renderRoomPage();

    expect(screen.getByText('Chargement…')).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: 'Salle K7P2QX' })).toBeInTheDocument();
    expect(screen.getByText('Template : Chips')).toBeInTheDocument();
    expect(screen.getByLabelText('Lien de la salle')).toHaveValue(aliceRoom.link);
    const participants: HTMLElement = screen.getByRole('heading', { name: 'Participants (2)' });
    expect(participants).toBeInTheDocument();
    expect(screen.getByText('Alice').closest('li')).toHaveTextContent('Alice(room admin)');
    expect(screen.getByText('Bob').closest('li')).not.toHaveTextContent('room admin');
    const summary: HTMLElement = settingsSummary();
    for (const line of [
      'Ordre du template',
      'Item suivant à la main',
      'Cooldown final de 60 s',
      'Le room admin joue',
      'Arrivées autorisées pendant la partie',
    ]) {
      expect(within(summary).getByText(line)).toBeInTheDocument();
    }
    expect(screen.getByRole('button', { name: 'Modifier' })).toBeInTheDocument();
  });

  it('shows who is online', async () => {
    stubBackend({ 'GET /rooms/K7P2QX': () => Response.json(aliceRoom) });

    renderRoomPage();

    expect(await screen.findByText('Alice')).toBeInTheDocument();
    expect(screen.getByText('Alice').closest('li')).toHaveTextContent('en ligne');
    expect(screen.getByText('Bob').closest('li')).toHaveTextContent('hors ligne');
  });

  it('says when live updates are unavailable', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    stubBackend({ 'GET /rooms/K7P2QX': () => Response.json(aliceRoom) });
    renderRoomPage();
    await screen.findByText('Alice');

    for (let failure = 0; failure < 5; failure += 1) {
      act(() => {
        latestSocket().closeFromServer(1006);
        vi.advanceTimersByTime(10_000);
      });
    }

    expect(await screen.findByRole('status')).toHaveTextContent(
      'Mises à jour en direct indisponibles',
    );
    vi.useRealTimers();
  });

  it('copies the link and announces it', async () => {
    const writeText: (text: string) => Promise<void> = vi.fn(async () => {});
    stubClipboard(writeText);
    stubBackend({ 'GET /rooms/K7P2QX': () => Response.json(aliceRoom) });
    renderRoomPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Copier le lien' }));

    expect(await screen.findByText('Lien copié')).toBeInTheDocument();
    expect(writeText).toHaveBeenCalledWith(aliceRoom.link);
  });

  it('asks to copy the link by hand when the clipboard refuses', async () => {
    stubClipboard(async () => {
      throw new Error('denied');
    });
    stubBackend({ 'GET /rooms/K7P2QX': () => Response.json(aliceRoom) });
    renderRoomPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Copier le lien' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('copiez-le à la main');
  });

  it('joins the room as a player when the user has no seat yet', async () => {
    const bobRoom: Room = { ...aliceRoom, is_admin: false };
    const fetchMock: BackendMock = stubBackend({
      ...signedInSession,
      'GET /rooms/K7P2QX': () => errorResponse(404, 'room_not_found'),
      'POST /rooms/K7P2QX/join': () => Response.json(bobRoom),
    });

    // Code tapé en minuscules : la salle est lue et rejointe sous son code canonique
    renderRoomPage('k7p2qx');

    expect(await screen.findByRole('heading', { name: 'Salle K7P2QX' })).toBeInTheDocument();
    expect(calledRoutes(fetchMock).filter((route) => route.includes('/rooms/'))).toEqual([
      'GET /rooms/K7P2QX',
      'POST /rooms/K7P2QX/join',
    ]);
    expect(screen.queryByRole('button', { name: 'Modifier' })).not.toBeInTheDocument();
  });

  it('says the room cannot be found', async () => {
    // Le cache de requêtes journalise l'erreur attendue
    const consoleError: MockInstance = vi.spyOn(console, 'error').mockImplementation(() => {});
    stubBackend({
      ...signedInSession,
      'GET /rooms/ZZZZZZ': () => errorResponse(404, 'room_not_found'),
      'POST /rooms/ZZZZZZ/join': () => errorResponse(404, 'room_not_found'),
    });

    renderRoomPage('ZZZZZZ');

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Cette salle est introuvable ou a été fermée.',
    );
    consoleError.mockRestore();
  });

  it('warns when the template of the room was deleted', async () => {
    stubBackend({ 'GET /rooms/K7P2QX': () => Response.json({ ...aliceRoom, template: null }) });

    renderRoomPage();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Le template de cette salle a été supprimé',
    );
    expect(screen.queryByText(/Template :/)).not.toBeInTheDocument();
  });

  it('only lets the room admin edit the settings', async () => {
    stubBackend({ 'GET /rooms/K7P2QX': () => Response.json({ ...aliceRoom, is_admin: false }) });

    renderRoomPage();

    await screen.findByRole('heading', { name: 'Réglages' });
    expect(within(settingsSummary()).getByText('Ordre du template')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Modifier' })).not.toBeInTheDocument();
  });

  it('shows that a game is in progress', async () => {
    stubBackend({ 'GET /rooms/K7P2QX': () => Response.json({ ...aliceRoom, status: 'playing' }) });

    renderRoomPage();

    expect(await screen.findByText('Partie en cours')).toBeInTheDocument();
  });
});
