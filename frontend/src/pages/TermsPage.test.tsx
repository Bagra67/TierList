import { screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import App from '../App';
import { LEGAL_CONTACT_EMAIL } from '../constants/legal';
import { changeLanguage } from '../i18n';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { stubBackend, unauthorized } from '../test/stubBackend';

// L'application entière, sans session : la page doit s'ouvrir sans demander de se connecter
function renderTermsPage() {
  stubBackend({ 'POST /auth/refresh': unauthorized });
  return renderWithQueryClient(
    <MemoryRouter initialEntries={['/terms']}>
      <App />
    </MemoryRouter>,
  );
}

describe('TermsPage', () => {
  afterEach(async () => {
    vi.unstubAllGlobals();
    await changeLanguage('fr');
  });

  it('shows the terms without an account, with their date', async () => {
    renderTermsPage();

    expect(
      await screen.findByRole('heading', { level: 1, name: "Conditions d'utilisation" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/^Dernière mise à jour : .*2026/)).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Connexion' })).not.toBeInTheDocument();
  });

  it('lists every section of the terms', async () => {
    renderTermsPage();
    await screen.findByRole('heading', { level: 1, name: "Conditions d'utilisation" });

    const sections: string[] = screen
      .getAllByRole('heading', { level: 2 })
      .map((heading) => heading.textContent ?? '');
    expect(sections).toEqual([
      'Le service',
      'Votre compte',
      'Jouer en invité',
      'Vos contenus',
      'Ce que voient les autres',
      'Signaler un contenu',
      'Suspension et suppression',
      'Disponibilité',
      'Responsabilité',
      'Droit applicable',
      'Modifications',
      'Contact',
    ]);
  });

  it('says that the results link can be opened by anyone who has it', async () => {
    renderTermsPage();

    expect(
      await screen.findByText(/peut être ouvert par toute personne qui le possède/),
    ).toBeInTheDocument();
  });

  it('gives the address to report content and to contact', async () => {
    renderTermsPage();
    await screen.findByRole('heading', { level: 2, name: 'Signaler un contenu' });

    const links: HTMLElement[] = screen.getAllByRole('link', { name: LEGAL_CONTACT_EMAIL });
    expect(links).toHaveLength(2);
    for (const link of links) {
      expect(link).toHaveAttribute('href', `mailto:${LEGAL_CONTACT_EMAIL}`);
    }
  });

  it('is translated into English', async () => {
    await changeLanguage('en');
    renderTermsPage();

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Terms of use' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: 'Report content' })).toBeInTheDocument();
  });
});
