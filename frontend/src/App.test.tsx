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

    expect(await screen.findByRole('heading', { name: 'Accueil' })).toBeInTheDocument();
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

  it('sends a signed-in user away from the login page', async () => {
    stubBackend(loggedInBackend);

    renderAppAt('/login');

    expect(await screen.findByRole('heading', { name: 'Accueil' })).toBeInTheDocument();
  });

  it('returns to the requested page, query string included, after signing in', async () => {
    stubBackend({
      'POST /auth/refresh': unauthorized,
      'POST /auth/login': tokenResponse('login-token'),
      'GET /auth/me': () => Response.json(alice),
    });
    renderAppAt('/?confirm=delete-account');
    await screen.findByRole('heading', { name: 'Connexion' });

    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'alice@example.com' } });
    fireEvent.change(screen.getByLabelText('Mot de passe'), { target: { value: 'secret' } });
    fireEvent.click(screen.getByRole('button', { name: 'Se connecter' }));

    // ?confirm=delete-account rouvre le dialogue de suppression sur la page d'accueil
    expect(await screen.findByRole('dialog', { name: 'Supprimer mon compte' })).toBeVisible();
  });

  it('shows a not found page for unknown urls, with or without a session', async () => {
    stubBackend({ 'POST /auth/refresh': unauthorized });

    renderAppAt('/does-not-exist');

    expect(await screen.findByRole('heading', { name: 'Page introuvable' })).toBeInTheDocument();
  });
});
