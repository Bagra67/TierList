import { fireEvent, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { setAccessToken } from './api/client';
import App from './App';
import { closedGameResults, RESULTS_TOKEN } from './test/fixtures/results';
import { renderWithQueryClient } from './test/renderWithQueryClient';
import {
  alice,
  signedInSession,
  stubBackend,
  tokenResponse,
  unauthorized,
} from './test/stubBackend';

// Seul fetch est remplacé : routeur, hooks, client API et TanStack Query tournent pour de vrai
function renderAppAt(path: string) {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

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
    stubBackend(signedInSession);

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

  it('logs out from the header and goes back to the login page', async () => {
    stubBackend({
      ...signedInSession,
      'GET /templates': () => Response.json({ items: [] }),
      'POST /auth/logout': () => new Response(null, { status: 204 }),
    });
    // Depuis une autre page que l'accueil : le bouton est dans l'en-tête de toutes les pages
    renderAppAt('/templates');
    await screen.findByRole('heading', { name: 'Mes templates' });

    fireEvent.click(
      within(screen.getByRole('banner')).getByRole('button', { name: 'Se déconnecter' }),
    );

    expect(await screen.findByRole('heading', { name: 'Connexion' })).toBeInTheDocument();
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Se déconnecter' })).not.toBeInTheDocument();
  });

  it('goes back to the signed-out state when the session ends elsewhere', async () => {
    // La session est restaurée au chargement, puis se termine ailleurs (autre onglet, refresh
    // token expiré) : le rafraîchissement suivant répond 401
    let sessionOpen: boolean = true;
    stubBackend({
      'POST /auth/refresh': () => (sessionOpen ? tokenResponse('alice-token')() : unauthorized()),
      'GET /auth/me': () => Response.json(alice),
      'GET /templates': () => (sessionOpen ? Response.json({ items: [] }) : unauthorized()),
      'GET /history': () => unauthorized(),
    });
    renderAppAt('/templates');
    const nav = await screen.findByRole('navigation', { name: 'Navigation principale' });
    sessionOpen = false;

    fireEvent.click(within(nav).getByRole('link', { name: 'Historique' }));

    expect(await screen.findByRole('heading', { name: 'Connexion' })).toBeInTheDocument();
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Se déconnecter' })).not.toBeInTheDocument();
  });

  it('sends a signed-in user away from the login page', async () => {
    stubBackend(signedInSession);

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

  it('shows the navigation once signed in and opens my templates', async () => {
    stubBackend({ ...signedInSession, 'GET /templates': () => Response.json({ items: [] }) });
    renderAppAt('/');

    const nav = await screen.findByRole('navigation', { name: 'Navigation principale' });
    fireEvent.click(within(nav).getByRole('link', { name: 'Mes templates' }));

    expect(await screen.findByRole('heading', { name: 'Mes templates' })).toBeInTheDocument();
    expect(within(nav).getByRole('link', { name: 'Mes templates' })).toHaveAttribute(
      'aria-current',
      'page',
    );
  });

  it('opens my history from the navigation', async () => {
    stubBackend({
      ...signedInSession,
      'GET /history': () => Response.json({ games: [], has_more: false }),
    });
    renderAppAt('/');

    const nav = await screen.findByRole('navigation', { name: 'Navigation principale' });
    fireEvent.click(within(nav).getByRole('link', { name: 'Historique' }));

    expect(await screen.findByRole('heading', { name: 'Historique' })).toBeInTheDocument();
  });

  it('protects my history without a session', async () => {
    stubBackend({ 'POST /auth/refresh': unauthorized });

    renderAppAt('/history');

    expect(await screen.findByRole('heading', { name: 'Connexion' })).toBeInTheDocument();
  });

  it('hides the navigation and protects my templates without a session', async () => {
    stubBackend({ 'POST /auth/refresh': unauthorized });

    renderAppAt('/templates');

    expect(await screen.findByRole('heading', { name: 'Connexion' })).toBeInTheDocument();
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
  });

  it('opens the public results link without a session, without asking to sign in', async () => {
    stubBackend({
      'POST /auth/refresh': unauthorized,
      [`GET /results/${RESULTS_TOKEN}`]: () => Response.json(closedGameResults),
    });

    renderAppAt(`/results/${RESULTS_TOKEN}`);

    expect(await screen.findByRole('heading', { name: 'Résultats : Épices' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Connexion' })).not.toBeInTheDocument();
    // Sans compte, l'en-tête n'a ni les liens privés ni « Se déconnecter »
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Se déconnecter' })).not.toBeInTheDocument();
  });

  it('shows a not found page for unknown urls, with or without a session', async () => {
    stubBackend({ 'POST /auth/refresh': unauthorized });

    renderAppAt('/does-not-exist');

    expect(await screen.findByRole('heading', { name: 'Page introuvable' })).toBeInTheDocument();
  });
});
