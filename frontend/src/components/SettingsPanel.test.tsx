import { fireEvent, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { setAccessToken } from '../api/client';
import App from '../App';
import { changeLanguage } from '../i18n';
import { DARK_CLASS } from '../constants/theme';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { signedInSession, stubBackend, unauthorized } from '../test/stubBackend';

// L'application entière : le panneau vit dans l'en-tête de Layout, sur toutes les pages
function renderAppAt(path: string) {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

async function openPanel(): Promise<HTMLElement> {
  fireEvent.click(await screen.findByRole('button', { name: 'Paramètres' }));
  return screen.getByRole('dialog', { name: 'Paramètres' });
}

describe('SettingsPanel', () => {
  afterEach(async () => {
    setAccessToken(null);
    vi.unstubAllGlobals();
    await changeLanguage('fr');
  });

  it('opens from the gear button and closes with its close button', async () => {
    stubBackend({ 'POST /auth/refresh': unauthorized });
    renderAppAt('/login');

    const panel: HTMLElement = await openPanel();
    expect(panel).toBeVisible();

    fireEvent.click(within(panel).getByRole('button', { name: 'Fermer' }));

    expect(screen.queryByRole('dialog', { name: 'Paramètres' })).not.toBeInTheDocument();
  });

  it('changes the theme and the language from the panel', async () => {
    stubBackend({ 'POST /auth/refresh': unauthorized });
    renderAppAt('/login');
    const panel: HTMLElement = await openPanel();

    fireEvent.change(within(panel).getByLabelText('Thème'), { target: { value: 'dark' } });
    fireEvent.change(within(panel).getByLabelText('Langue'), { target: { value: 'en' } });

    expect(document.documentElement).toHaveClass(DARK_CLASS);
    expect(await screen.findByRole('dialog', { name: 'Settings' })).toBeVisible();
  });

  it('hides the account section when signed out', async () => {
    stubBackend({ 'POST /auth/refresh': unauthorized });
    renderAppAt('/login');

    const panel: HTMLElement = await openPanel();

    expect(within(panel).queryByRole('heading', { name: 'Compte' })).not.toBeInTheDocument();
    expect(
      within(panel).queryByRole('button', { name: 'Supprimer mon compte' }),
    ).not.toBeInTheDocument();
  });

  it('deletes the account from the panel, then closes it on the login page', async () => {
    stubBackend({
      ...signedInSession,
      'DELETE /auth/me': () => new Response(null, { status: 204 }),
    });
    renderAppAt('/');
    await screen.findByText(/Connecté en tant que Alice/);
    const panel: HTMLElement = await openPanel();
    expect(within(panel).getByRole('heading', { name: 'Compte' })).toBeInTheDocument();

    fireEvent.click(within(panel).getByRole('button', { name: 'Supprimer mon compte' }));
    const deletion: HTMLElement = screen.getByRole('dialog', { name: 'Supprimer mon compte' });
    fireEvent.change(within(deletion).getByLabelText('Mot de passe'), {
      target: { value: 'secret' },
    });
    fireEvent.click(within(deletion).getByRole('button', { name: 'Supprimer définitivement' }));

    expect(await screen.findByRole('heading', { name: 'Connexion' })).toBeInTheDocument();
    expect(screen.queryByRole('dialog', { name: 'Paramètres' })).not.toBeInTheDocument();
  });

  it('reopens the account deletion in the panel after a Google sign-in', async () => {
    stubBackend(signedInSession);

    renderAppAt('/?confirm=delete-account');

    expect(await screen.findByRole('dialog', { name: 'Supprimer mon compte' })).toBeVisible();
    expect(screen.getByRole('dialog', { name: 'Paramètres' })).toBeVisible();
  });
});
