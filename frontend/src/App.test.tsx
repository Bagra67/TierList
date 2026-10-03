import { fireEvent, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { setAccessToken } from './api/client';
import App from './App';
import { renderWithQueryClient } from './test/renderWithQueryClient';
import { alice, stubBackend, tokenResponse, unauthorized } from './test/stubBackend';

// Seul fetch est remplacé : routeur, hooks, client API et TanStack Query tournent pour de vrai
function renderAppAt(path: string) {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

const loggedInBackend = {
  'POST /auth/refresh': tokenResponse('restored-token'),
  'GET /auth/me': () => Response.json(alice),
  'GET /hello': () => Response.json({ message: 'Hello World' }),
};

describe('App', () => {
  afterEach(() => {
    setAccessToken(null);
    vi.unstubAllGlobals();
  });

  it('redirects to the login page without a session', async () => {
    stubBackend({ 'POST /auth/refresh': unauthorized });

    renderAppAt('/');

    expect(await screen.findByRole('heading', { name: 'Connexion' })).toBeInTheDocument();
  });

  it('restores the session and shows the home page', async () => {
    stubBackend(loggedInBackend);

    renderAppAt('/');

    expect(await screen.findByRole('heading', { name: 'Hello World' })).toBeInTheDocument();
    expect(screen.getByText(/Connecté en tant que Alice/)).toBeInTheDocument();
  });

  it('shows an alert when the backend cannot be reached', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    stubBackend({ 'POST /auth/refresh': () => new Response(null, { status: 502 }) });

    renderAppAt('/');

    expect(await screen.findByRole('alert')).toHaveTextContent('Impossible de joindre le backend');
    consoleError.mockRestore();
  });

  it('logs out and goes back to the login page', async () => {
    stubBackend({
      ...loggedInBackend,
      'POST /auth/logout': () => new Response(null, { status: 204 }),
    });
    renderAppAt('/');

    fireEvent.click(await screen.findByRole('button', { name: 'Se déconnecter' }));

    expect(await screen.findByRole('heading', { name: 'Connexion' })).toBeInTheDocument();
  });

  it('redirects unknown pages to the home page', async () => {
    stubBackend(loggedInBackend);

    renderAppAt('/does-not-exist');

    expect(await screen.findByRole('heading', { name: 'Hello World' })).toBeInTheDocument();
  });
});
