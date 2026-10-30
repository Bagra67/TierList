import { screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { setAccessToken } from '../api/client';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import {
  type StubbedRoute,
  calledRoutes,
  signedInSession,
  stubBackend,
  unauthorized,
} from '../test/stubBackend';
import { HomePage } from './HomePage';

function renderHomePage() {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={['/']}>
      <HomePage />
    </MemoryRouter>,
  );
}

// Quatre modèles et quatre parties : l'accueil n'en montre que trois de chaque
const fourTemplates = ['Épices', 'Fromages', 'Fruits', 'Desserts'].map((name, index) => ({
  id: `template-${index}`,
  name,
  tile_count: 5 + index,
  updated_at: '2026-10-29T10:00:00Z',
}));
const fourGames = ['Épices', 'Fromages', 'Fruits', 'Desserts'].map((name, index) => ({
  public_token: `token-${index}`,
  template_name: name,
  closed_at: '2026-10-28T20:00:00Z',
  player_count: 3,
}));

function signedInWith(templates: object[], games: object[]): Record<string, StubbedRoute> {
  return {
    ...signedInSession,
    'GET /templates': () => Response.json({ items: templates }),
    'GET /history': () => Response.json({ games, has_more: false }),
  };
}

describe('HomePage', () => {
  afterEach(() => {
    setAccessToken(null);
    vi.unstubAllGlobals();
  });

  it('shows the visitor home without a session, with the join field and the sign-up', async () => {
    const backend = stubBackend({ 'POST /auth/refresh': unauthorized });

    renderHomePage();

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Classez ensemble, en direct.' }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('Code de la salle')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Créer un compte' })).toHaveAttribute(
      'href',
      '/register',
    );
    expect(screen.getByRole('link', { name: "J'ai déjà un compte" })).toHaveAttribute(
      'href',
      '/login',
    );
    // Rien de personnel n'est lu sans session
    expect(calledRoutes(backend)).not.toContain('GET /templates');
    expect(calledRoutes(backend)).not.toContain('GET /history');
  });

  it('explains a game in three steps to the visitor', async () => {
    stubBackend({ 'POST /auth/refresh': unauthorized });

    renderHomePage();

    const steps: HTMLElement = within(
      await screen.findByRole('region', { name: 'Comment ça marche' }),
    ).getByRole('list');
    expect(within(steps).getAllByRole('listitem')).toHaveLength(3);
    expect(within(steps).getAllByRole('listitem')[0]).toHaveTextContent('Préparez un modèle');
  });

  it('hides the example board from screen readers and describes it instead', async () => {
    stubBackend({ 'POST /auth/refresh': unauthorized });

    renderHomePage();

    const board: HTMLElement = await screen.findByRole('figure');
    expect(within(board).getByText(/^Exemple de tier list/)).toBeInTheDocument();
    const pizza: HTMLElement = within(board).getByText('Pizza');
    expect(pizza.closest('[aria-hidden="true"]')).not.toBeNull();
    // Les éléments apparaissent un à un, sauf en mouvement réduit (classe motion-safe)
    expect(pizza.parentElement).toHaveClass('motion-safe:animate-reveal');
  });

  it('greets the signed-in player with their three latest templates and games', async () => {
    stubBackend(signedInWith(fourTemplates, fourGames));

    renderHomePage();

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Prêt pour une partie, Alice ?' }),
    ).toBeInTheDocument();
    const templates: HTMLElement = await screen.findByRole('region', { name: 'Vos modèles' });
    expect(await within(templates).findAllByRole('listitem')).toHaveLength(3);
    expect(
      within(templates).getByRole('button', { name: 'Créer une salle avec Épices' }),
    ).toBeInTheDocument();
    expect(within(templates).getByRole('link', { name: 'Tous mes modèles' })).toHaveAttribute(
      'href',
      '/templates',
    );
    const games: HTMLElement = screen.getByRole('region', { name: 'Vos dernières parties' });
    expect(await within(games).findAllByRole('listitem')).toHaveLength(3);
    expect(
      within(games).getByRole('link', { name: 'Voir les résultats de la partie Épices' }),
    ).toHaveAttribute('href', '/results/token-0');
    // Pas de vitrine pour un joueur connecté
    expect(screen.queryByRole('link', { name: 'Créer un compte' })).not.toBeInTheDocument();
  });

  it('leads a new player to prepare a template, with no game yet', async () => {
    stubBackend(signedInWith([], []));

    renderHomePage();

    const templates: HTMLElement = await screen.findByRole('region', { name: 'Vos modèles' });
    expect(await within(templates).findByText(/^Aucun modèle pour l'instant/)).toBeInTheDocument();
    expect(within(templates).getByRole('link', { name: 'Préparer un modèle' })).toHaveAttribute(
      'href',
      '/templates',
    );
    const games: HTMLElement = screen.getByRole('region', { name: 'Vos dernières parties' });
    expect(await within(games).findByText(/^Aucune partie terminée/)).toBeInTheDocument();
  });
});
