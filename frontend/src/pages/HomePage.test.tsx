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

function popularTemplatesRoute(name: string): StubbedRoute {
  return () =>
    Response.json({
      items: [
        {
          id: 'template-popular',
          name,
          owner_name: 'Camille',
          tags: [],
          tile_count: 6,
          like_count: 12,
          preview_image_url: null,
          preview_image_removed: false,
          tier_colors: ['#FF3B6B'],
        },
      ],
      next_cursor: null,
    });
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
    expect(calledRoutes(backend)).not.toContain('GET /templates');
    expect(calledRoutes(backend)).not.toContain('GET /history');
  });

  it('shows the visitor the most liked public templates and a way to all of them', async () => {
    const backend = stubBackend({
      'POST /auth/refresh': unauthorized,
      'GET /marketplace/templates': popularTemplatesRoute('Fromages'),
    });

    renderHomePage();

    const section: HTMLElement = await screen.findByRole('region', {
      name: 'Modèles publics populaires',
    });
    expect(within(section).getByRole('link', { name: 'Fromages' })).toHaveAttribute(
      'href',
      '/marketplace/templates/template-popular',
    );
    expect(
      within(section).getByRole('link', { name: 'Voir tous les modèles publics' }),
    ).toHaveAttribute('href', '/marketplace');
    const request: Request | undefined = backend.mock.calls
      .map(([sent]) => sent)
      .find((sent) => sent.url.includes('/marketplace/templates'));
    expect(new URL(request?.url ?? '').searchParams.get('limit')).toBe('3');
  });

  it('shows no public template section to a visitor when there is none', async () => {
    stubBackend({
      'POST /auth/refresh': unauthorized,
      'GET /marketplace/templates': () => Response.json({ items: [], next_cursor: null }),
    });

    renderHomePage();

    await screen.findByRole('region', { name: 'Comment ça marche' });
    expect(
      screen.queryByRole('region', { name: 'Modèles publics populaires' }),
    ).not.toBeInTheDocument();
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
    expect(screen.queryByRole('link', { name: 'Créer un compte' })).not.toBeInTheDocument();
  });

  it('shows the signed-in player the most liked public templates too', async () => {
    stubBackend({
      ...signedInWith(fourTemplates, fourGames),
      'GET /marketplace/templates': popularTemplatesRoute('Fromages du monde'),
    });

    renderHomePage();

    const section: HTMLElement = await screen.findByRole('region', {
      name: 'Modèles publics populaires',
    });
    expect(within(section).getByRole('link', { name: 'Fromages du monde' })).toBeInTheDocument();
    expect(
      within(section).getByRole('link', { name: 'Voir tous les modèles publics' }),
    ).toHaveAttribute('href', '/marketplace');
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
