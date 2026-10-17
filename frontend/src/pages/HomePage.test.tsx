import { screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { setAccessToken } from '../api/client';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { signedInSession, stubBackend } from '../test/stubBackend';
import { HomePage } from './HomePage';

function renderHomePage(path = '/') {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={[path]}>
      <HomePage />
    </MemoryRouter>,
  );
}

describe('HomePage', () => {
  afterEach(() => {
    setAccessToken(null);
    vi.unstubAllGlobals();
  });

  it('shows the page title and the connected user', async () => {
    stubBackend(signedInSession);

    renderHomePage();

    expect(screen.getByRole('heading', { name: 'Accueil' })).toBeInTheDocument();
    expect(await screen.findByText(/Connecté en tant que Alice/)).toBeInTheDocument();
  });

  it('reopens the account deletion after a Google sign-in', async () => {
    stubBackend(signedInSession);

    renderHomePage('/?confirm=delete-account');

    expect(await screen.findByRole('dialog', { name: 'Supprimer mon compte' })).toBeVisible();
  });
});
