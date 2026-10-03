import { screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { setAccessToken } from '../api/client';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { alice, stubBackend, tokenResponse } from '../test/stubBackend';
import { HomePage } from './HomePage';

function renderHomePage(path = '/') {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={[path]}>
      <HomePage />
    </MemoryRouter>,
  );
}

const session = {
  'POST /auth/refresh': tokenResponse('restored-token'),
  'GET /auth/me': () => Response.json(alice),
};

describe('HomePage', () => {
  afterEach(() => {
    setAccessToken(null);
    vi.unstubAllGlobals();
  });

  it('shows a loading message while the backend answers', () => {
    stubBackend({ ...session, 'GET /hello': () => new Promise<Response>(() => {}) });

    renderHomePage();

    expect(screen.getByText('Chargement…')).toBeInTheDocument();
  });

  it('shows the message returned by the backend and the connected user', async () => {
    stubBackend({ ...session, 'GET /hello': () => Response.json({ message: 'Hello World' }) });

    renderHomePage();

    expect(await screen.findByRole('heading', { name: 'Hello World' })).toBeInTheDocument();
    expect(await screen.findByText(/Connecté en tant que Alice/)).toBeInTheDocument();
  });

  it('shows an alert when the backend cannot be reached', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    stubBackend({ ...session, 'GET /hello': () => new Response(null, { status: 500 }) });

    renderHomePage();

    expect(await screen.findByRole('alert')).toHaveTextContent('Impossible de joindre le backend');
    expect(consoleError).toHaveBeenCalled();
    consoleError.mockRestore();
  });

  it('reopens the account deletion after a Google sign-in', async () => {
    stubBackend({ ...session, 'GET /hello': () => Response.json({ message: 'Hello World' }) });

    renderHomePage('/?confirm=delete-account');

    expect(await screen.findByRole('dialog', { name: 'Supprimer mon compte' })).toBeVisible();
  });
});
