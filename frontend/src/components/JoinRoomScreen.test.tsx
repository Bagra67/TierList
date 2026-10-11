import { fireEvent, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, type MockInstance, vi } from 'vitest';

import { aliceRoom, lousRoom, renderRoomPage } from '../test/rooms';
import { calledRoutes, errorResponse, stubBackend } from '../test/stubBackend';

type BackendMock = ReturnType<typeof stubBackend>;

// Corps de la première requête reçue sur cette route
async function requestBody(fetchMock: BackendMock, route: string): Promise<unknown> {
  const call = fetchMock.mock.calls.find(
    ([request]) => `${request.method} ${new URL(request.url).pathname}` === `POST /api${route}`,
  );
  if (call === undefined) throw new Error(`No request to ${route}`);
  return call[0].clone().json();
}

// Visiteur sans compte (aucune session) et sans place : GET /rooms/K7P2QX répond 404
const visitorWithoutSeat = {
  'GET /rooms/K7P2QX': () => errorResponse(404, 'room_not_found'),
};

describe('JoinRoomScreen', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('offers to sign in or to join as a guest', async () => {
    stubBackend(visitorWithoutSeat);

    renderRoomPage();

    expect(await screen.findByRole('heading', { name: 'Rejoindre la salle' })).toBeInTheDocument();
    expect(screen.getByText('K7P2QX')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Se connecter' })).toHaveAttribute('href', '/login');
  });

  it('comes back to the room after signing in', async () => {
    stubBackend(visitorWithoutSeat);
    renderRoomPage();

    fireEvent.click(await screen.findByRole('link', { name: 'Se connecter' }));

    expect(await screen.findByRole('heading', { name: 'Connexion' })).toBeInTheDocument();
  });

  it('joins as a guest and shows the personal link', async () => {
    const fetchMock: BackendMock = stubBackend({
      ...visitorWithoutSeat,
      'POST /rooms/K7P2QX/guests': () => Response.json(lousRoom, { status: 201 }),
    });
    renderRoomPage();

    fireEvent.change(await screen.findByLabelText('Pseudo'), { target: { value: 'Lou' } });
    fireEvent.click(screen.getByRole('button', { name: 'Rejoindre en invité' }));

    expect(await screen.findByRole('heading', { name: 'Salle K7P2QX' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Rejoindre la salle' })).not.toBeInTheDocument();
    const notice: HTMLElement = screen
      .getByRole('heading', { name: 'Votre lien perso' })
      .closest('section') as HTMLElement;
    expect(within(notice).getByLabelText('Lien perso')).toHaveValue(lousRoom.guest_link);
    expect(notice).toHaveTextContent("jusqu'au 10 novembre 2026");
    expect(screen.getByText('Lou').closest('li')).toHaveTextContent('Lou(invité)');
    expect(screen.queryByRole('button', { name: 'Modifier' })).not.toBeInTheDocument();
    expect(await requestBody(fetchMock, '/rooms/K7P2QX/guests')).toEqual({ nickname: 'Lou' });
  });

  it('says when the nickname is already used', async () => {
    stubBackend({
      ...visitorWithoutSeat,
      'POST /rooms/K7P2QX/guests': () => errorResponse(409, 'nickname_taken'),
    });
    renderRoomPage();

    fireEvent.change(await screen.findByLabelText('Pseudo'), { target: { value: 'Alice' } });
    fireEvent.click(screen.getByRole('button', { name: 'Rejoindre en invité' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Ce pseudo est déjà pris dans cette salle.',
    );
  });

  it('shows the error of the nickname field', async () => {
    stubBackend({
      ...visitorWithoutSeat,
      'POST /rooms/K7P2QX/guests': () =>
        errorResponse(422, 'validation_error', {
          errors: [
            {
              field: 'body.nickname',
              message: 'String should have at most 50 characters',
              code: 'string_too_long',
              params: { max_length: 50 },
            },
          ],
        }),
    });
    renderRoomPage();

    fireEvent.change(await screen.findByLabelText('Pseudo'), { target: { value: 'L'.repeat(51) } });
    fireEvent.click(screen.getByRole('button', { name: 'Rejoindre en invité' }));

    expect(await screen.findByText('Au plus 50 caractères.')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('a returning guest is recognised by the cookie and enters the lobby', async () => {
    stubBackend({ 'GET /rooms/K7P2QX': () => Response.json({ ...aliceRoom, is_admin: false }) });

    renderRoomPage();

    expect(await screen.findByRole('heading', { name: 'Salle K7P2QX' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Votre lien perso' })).not.toBeInTheDocument();
  });

  it('restores the seat from the personal link and removes the token from the address', async () => {
    const fetchMock: BackendMock = stubBackend({
      'POST /rooms/K7P2QX/guest-session': () => Response.json(lousRoom),
    });

    renderRoomPage('K7P2QX#guest=lou-token');

    expect(await screen.findByRole('heading', { name: 'Salle K7P2QX' })).toBeInTheDocument();
    expect(await requestBody(fetchMock, '/rooms/K7P2QX/guest-session')).toEqual({
      token: 'lou-token',
    });
    expect(calledRoutes(fetchMock)).not.toContain('GET /rooms/K7P2QX');
    await vi.waitFor(() => expect(screen.getByTestId('location-hash')).toBeEmptyDOMElement());
  });

  it('says when the personal link is no longer valid, then offers to join again', async () => {
    // Le cache de requêtes journalise l'erreur attendue
    const consoleError: MockInstance = vi.spyOn(console, 'error').mockImplementation(() => {});
    stubBackend({
      'POST /rooms/K7P2QX/guest-session': () => errorResponse(404, 'guest_link_invalid'),
    });

    renderRoomPage('K7P2QX#guest=old-token');

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Ce lien perso a expiré, ou la salle a été fermée.',
    );
    expect(screen.getByRole('heading', { name: 'Rejoindre la salle' })).toBeInTheDocument();
    consoleError.mockRestore();
  });
});
