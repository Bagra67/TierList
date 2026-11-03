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
  superAdminSession,
  tokenResponse,
  unauthorized,
} from './test/stubBackend';

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

  it('shows the public home page without a session', async () => {
    stubBackend({ 'POST /auth/refresh': unauthorized });

    renderAppAt('/');

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Classez ensemble, en direct.' }),
    ).toBeInTheDocument();
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
  });

  it('restores the session and shows the home page', async () => {
    stubBackend(signedInSession);

    renderAppAt('/');

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Prêt pour une partie, Alice ?' }),
    ).toBeInTheDocument();
  });

  it('shows an alert when the backend cannot be reached', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    stubBackend({ 'POST /auth/refresh': () => new Response(null, { status: 502 }) });

    renderAppAt('/');

    expect(await screen.findByRole('alert')).toHaveTextContent('Le serveur ne répond pas');
    consoleError.mockRestore();
  });

  it('logs out from the header and goes back to the login page', async () => {
    stubBackend({
      ...signedInSession,
      'GET /templates': () => Response.json({ items: [] }),
      'POST /auth/logout': () => new Response(null, { status: 204 }),
    });
    renderAppAt('/templates');
    await screen.findByRole('heading', { name: 'Mes modèles' });

    fireEvent.click(
      within(screen.getByRole('banner')).getByRole('button', { name: 'Se déconnecter' }),
    );

    expect(await screen.findByRole('heading', { name: 'Connexion' })).toBeInTheDocument();
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Se déconnecter' })).not.toBeInTheDocument();
  });

  it('goes back to the signed-out state when the session ends elsewhere', async () => {
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

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Prêt pour une partie, Alice ?' }),
    ).toBeInTheDocument();
  });

  it('returns to the requested page, query string included, after signing in', async () => {
    stubBackend({
      'POST /auth/refresh': unauthorized,
      'POST /auth/login': tokenResponse('login-token'),
      'GET /auth/me': () => Response.json(alice),
      'GET /history': () => Response.json({ games: [], has_more: false }),
    });
    renderAppAt('/history?confirm=delete-account');
    await screen.findByRole('heading', { name: 'Connexion' });

    fireEvent.change(screen.getByLabelText('E-mail'), { target: { value: 'alice@example.com' } });
    fireEvent.change(screen.getByLabelText('Mot de passe'), { target: { value: 'secret' } });
    fireEvent.click(screen.getByRole('button', { name: 'Se connecter' }));

    expect(await screen.findByRole('dialog', { name: 'Supprimer mon compte' })).toBeVisible();
  });

  it('shows the navigation once signed in and opens my templates', async () => {
    stubBackend({ ...signedInSession, 'GET /templates': () => Response.json({ items: [] }) });
    renderAppAt('/');

    const nav = await screen.findByRole('navigation', { name: 'Navigation principale' });
    fireEvent.click(within(nav).getByRole('link', { name: 'Mes modèles' }));

    expect(await screen.findByRole('heading', { name: 'Mes modèles' })).toBeInTheDocument();
    expect(within(nav).getByRole('link', { name: 'Mes modèles' })).toHaveAttribute(
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

  it('shows the moderation link to a super admin and opens the moderation area', async () => {
    stubBackend({
      ...superAdminSession,
      'GET /moderation/reports': () => Response.json({ contents: [], has_more: false }),
      'GET /moderation/reports/count': () => Response.json({ open_contents: 3 }),
      'GET /moderation/games/hidden': () => Response.json({ games: [], has_more: false }),
      'GET /moderation/log': () => Response.json({ entries: [], has_more: false }),
      'GET /moderation/super-admins': () => Response.json([]),
    });
    renderAppAt('/');

    const nav = await screen.findByRole('navigation', { name: 'Navigation principale' });
    expect(await within(nav).findByLabelText('3 contenus signalés')).toHaveTextContent('3');
    fireEvent.click(within(nav).getByRole('link', { name: /^Modération/ }));

    expect(await screen.findByRole('heading', { name: 'Signalements' })).toBeInTheDocument();
    const moderationNav = screen.getByRole('navigation', { name: 'Espace de modération' });
    fireEvent.click(within(moderationNav).getByRole('link', { name: 'Journal' }));
    expect(
      await screen.findByRole('heading', { name: 'Journal de modération' }),
    ).toBeInTheDocument();
  });

  it('hides the moderation link from other accounts', async () => {
    stubBackend(signedInSession);
    renderAppAt('/');

    const nav = await screen.findByRole('navigation', { name: 'Navigation principale' });
    expect(within(nav).getByRole('link', { name: 'Historique' })).toBeInTheDocument();
    expect(within(nav).queryByRole('link', { name: 'Modération' })).not.toBeInTheDocument();
  });

  it('shows a not found page to other accounts on the moderation area', async () => {
    stubBackend(signedInSession);

    renderAppAt('/moderation');

    expect(await screen.findByRole('heading', { name: 'Page introuvable' })).toBeInTheDocument();
    expect(
      screen.queryByRole('heading', { name: 'Journal de modération' }),
    ).not.toBeInTheDocument();
  });

  it('protects the moderation area without a session', async () => {
    stubBackend({ 'POST /auth/refresh': unauthorized });

    renderAppAt('/moderation');

    expect(await screen.findByRole('heading', { name: 'Connexion' })).toBeInTheDocument();
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
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Se déconnecter' })).not.toBeInTheDocument();
  });

  it.each([
    ["Conditions d'utilisation", "Conditions d'utilisation"],
    ['Mentions légales', 'Mentions légales'],
  ])('opens the %s page from the footer, without a session', async (linkName, title) => {
    stubBackend({ 'POST /auth/refresh': unauthorized });
    renderAppAt('/login');
    await screen.findByRole('heading', { name: 'Connexion' });

    fireEvent.click(within(screen.getByRole('contentinfo')).getByRole('link', { name: linkName }));

    expect(await screen.findByRole('heading', { level: 1, name: title })).toBeInTheDocument();
  });

  it('opens the privacy policy from the footer, without a session', async () => {
    stubBackend({ 'POST /auth/refresh': unauthorized });
    renderAppAt('/login');
    await screen.findByRole('heading', { name: 'Connexion' });

    fireEvent.click(
      within(screen.getByRole('contentinfo')).getByRole('link', {
        name: 'Politique de confidentialité',
      }),
    );

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Politique de confidentialité' }),
    ).toBeInTheDocument();
  });

  it('shows a not found page for unknown urls, with or without a session', async () => {
    stubBackend({ 'POST /auth/refresh': unauthorized });

    renderAppAt('/does-not-exist');

    expect(await screen.findByRole('heading', { name: 'Page introuvable' })).toBeInTheDocument();
  });
});
