import { screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { setAccessToken } from '../api/client';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { signedInSession, stubBackend } from '../test/stubBackend';
import { HomePage } from './HomePage';

function renderHomePage() {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={['/']}>
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
    // « Se déconnecter » est dans l'en-tête de toutes les pages (LogoutButton), plus ici
    expect(screen.queryByRole('button', { name: 'Se déconnecter' })).not.toBeInTheDocument();
  });
});
