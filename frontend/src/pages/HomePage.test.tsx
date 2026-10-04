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

  it('shows the page title and the connected user', async () => {
    stubBackend(session);

    renderHomePage();

    expect(screen.getByRole('heading', { name: 'Accueil' })).toBeInTheDocument();
    expect(await screen.findByText(/Connecté en tant que Alice/)).toBeInTheDocument();
  });

  it('reopens the account deletion after a Google sign-in', async () => {
    stubBackend(session);

    renderHomePage('/?confirm=delete-account');

    expect(await screen.findByRole('dialog', { name: 'Supprimer mon compte' })).toBeVisible();
  });
});
