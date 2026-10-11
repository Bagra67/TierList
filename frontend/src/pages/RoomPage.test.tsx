import { fireEvent, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, type MockInstance, vi } from 'vitest';

import { aliceRoom, renderRoomPage, settingsSummary } from '../test/rooms';
import { errorResponse, stubBackend } from '../test/stubBackend';

// Presse-papiers simulé : jsdom n'en fournit pas
function stubClipboard(writeText: (text: string) => Promise<void>): void {
  Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true });
}

describe('RoomPage', () => {
  afterEach(() => {
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

  it('says the room cannot be found', async () => {
    // Le cache de requêtes journalise l'erreur attendue
    const consoleError: MockInstance = vi.spyOn(console, 'error').mockImplementation(() => {});
    stubBackend({ 'GET /rooms/ZZZZZZ': () => errorResponse(404, 'room_not_found') });

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
