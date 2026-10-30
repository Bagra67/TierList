import { fireEvent, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import App from '../App';
import {
  LEGAL_CONTACT_EMAIL,
  LEGAL_HOST_ADDRESS,
  LEGAL_HOST_NAME,
  LEGAL_HOST_PHONE,
} from '../constants/legal';
import { changeLanguage } from '../i18n';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { stubBackend, unauthorized } from '../test/stubBackend';

// L'application entière, sans session : la page doit s'ouvrir sans demander de se connecter
function renderLegalNoticePage() {
  stubBackend({ 'POST /auth/refresh': unauthorized });
  return renderWithQueryClient(
    <MemoryRouter initialEntries={['/legal']}>
      <App />
    </MemoryRouter>,
  );
}

describe('LegalNoticePage', () => {
  afterEach(async () => {
    vi.unstubAllGlobals();
    await changeLanguage('fr');
  });

  it('shows the publisher without an account, with the date and the contact', async () => {
    renderLegalNoticePage();

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Mentions légales' }),
    ).toBeInTheDocument();
    expect(screen.getByText(/^Dernière mise à jour : .*2026/)).toBeInTheDocument();
    expect(screen.getByText(/à titre non professionnel par Samuel Ladwein/)).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: LEGAL_CONTACT_EMAIL })[0]).toHaveAttribute(
      'href',
      `mailto:${LEGAL_CONTACT_EMAIL}`,
    );
    expect(screen.queryByRole('heading', { name: 'Connexion' })).not.toBeInTheDocument();
  });

  it('lists every section, with the host and how to report content', async () => {
    renderLegalNoticePage();
    await screen.findByRole('heading', { level: 1, name: 'Mentions légales' });

    const sections: string[] = screen
      .getAllByRole('heading', { level: 2 })
      .map((heading) => heading.textContent ?? '');
    expect(sections).toEqual([
      'Éditeur et directeur de la publication',
      'Hébergeur',
      'Autres prestataires',
      'Signaler un contenu',
      'Données personnelles',
    ]);
    for (const hostDetail of [LEGAL_HOST_NAME, LEGAL_HOST_ADDRESS, LEGAL_HOST_PHONE]) {
      expect(screen.getByText(hostDetail)).toBeInTheDocument();
    }
  });

  it('opens the privacy policy from the personal data section', async () => {
    renderLegalNoticePage();

    fireEvent.click(await screen.findByRole('link', { name: 'politique de confidentialité' }));

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Politique de confidentialité' }),
    ).toBeInTheDocument();
  });

  it('is translated into English', async () => {
    await changeLanguage('en');
    renderLegalNoticePage();

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Legal notice' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: 'Host' })).toBeInTheDocument();
  });
});
