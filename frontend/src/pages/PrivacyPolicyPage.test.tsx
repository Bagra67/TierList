import { screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import App from '../App';
import { CNIL_COMPLAINT_URL, LEGAL_CONTACT_EMAIL } from '../constants/legal';
import { changeLanguage } from '../i18n';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { stubBackend, unauthorized } from '../test/stubBackend';

// L'application entière, sans session : la page doit s'ouvrir sans demander de se connecter
function renderPrivacyPage() {
  stubBackend({ 'POST /auth/refresh': unauthorized });
  return renderWithQueryClient(
    <MemoryRouter initialEntries={['/privacy']}>
      <App />
    </MemoryRouter>,
  );
}

describe('PrivacyPolicyPage', () => {
  afterEach(async () => {
    vi.unstubAllGlobals();
    await changeLanguage('fr');
  });

  it('shows the policy without an account, with its date and controller', async () => {
    renderPrivacyPage();

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Politique de confidentialité' }),
    ).toBeInTheDocument();
    expect(screen.getByText(/^Dernière mise à jour : .*2026/)).toBeInTheDocument();
    expect(screen.getByText(/édité par Samuel Ladwein/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: LEGAL_CONTACT_EMAIL })).toHaveAttribute(
      'href',
      `mailto:${LEGAL_CONTACT_EMAIL}`,
    );
    expect(screen.queryByRole('heading', { name: 'Connexion' })).not.toBeInTheDocument();
  });

  it('lists every section of the policy', async () => {
    renderPrivacyPage();
    await screen.findByRole('heading', { level: 1, name: 'Politique de confidentialité' });

    const sections: string[] = screen
      .getAllByRole('heading', { level: 2 })
      .map((heading) => heading.textContent ?? '');
    expect(sections).toEqual([
      'Responsable du traitement',
      'Données collectées',
      'Pourquoi ces données',
      'Durées de conservation',
      'Qui voit vos données',
      'Prestataires',
      'Cookies et stockage local',
      'Sécurité',
      'Vos droits',
      'Modifications',
    ]);
  });

  it('describes the data of a content report and how long it is kept', async () => {
    renderPrivacyPage();

    expect(await screen.findByText(/^Signalements : l'adresse e-mail/)).toBeInTheDocument();
    expect(screen.getByText(/^Traiter les signalements de contenus illicites/)).toBeInTheDocument();
    expect(screen.getByText(/^Signalements : le temps de les traiter/)).toBeInTheDocument();
  });

  it('links to the CNIL complaint page in a new tab', async () => {
    renderPrivacyPage();

    const link: HTMLElement = await screen.findByRole('link', {
      name: 'déposer une plainte sur cnil.fr',
    });
    expect(link).toHaveAttribute('href', CNIL_COMPLAINT_URL);
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noreferrer');
  });

  it('is translated into English', async () => {
    await changeLanguage('en');
    renderPrivacyPage();

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Privacy policy' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: 'Your rights' })).toBeInTheDocument();
  });
});
