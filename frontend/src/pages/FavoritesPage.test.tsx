import { fireEvent, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { MarketplaceTemplate } from '../api/marketplace';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { alice, errorResponse, type StubbedRoute, stubBackend } from '../test/stubBackend';
import { FavoritesPage } from './FavoritesPage';

function card(id: string, name: string): MarketplaceTemplate {
  return {
    id,
    name,
    owner_name: 'Camille',
    featured: false,
    tags: ['Apéro'],
    tile_count: 8,
    like_count: 3,
    preview_image_url: null,
    preview_image_removed: false,
    tier_colors: ['#FF3B6B', '#FF8A2A'],
  };
}

const chips: MarketplaceTemplate = card('5d0c2a8e-1f3b-4c7a-9e21-3a4b5c6d7e01', 'Chips');
const sodas: MarketplaceTemplate = card('5d0c2a8e-1f3b-4c7a-9e21-3a4b5c6d7e02', 'Sodas');

function favoriteStates(templates: MarketplaceTemplate[]): Response {
  return Response.json({
    items: templates.map((template: MarketplaceTemplate) => ({
      template_id: template.id,
      favorited: true,
      can_favorite: true,
    })),
  });
}

function renderPage(routes: Record<string, StubbedRoute>) {
  stubBackend({ 'GET /marketplace/likes': () => Response.json({ items: [] }), ...routes });
  renderWithQueryClient(
    <MemoryRouter initialEntries={['/favorites']}>
      <Routes>
        <Route path="/favorites" element={<FavoritesPage />} />
        <Route path="/marketplace" element={<h1>Modèles publics</h1>} />
      </Routes>
    </MemoryRouter>,
    { currentUser: alice },
  );
}

describe('FavoritesPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('lists the favorites as cards of public templates', async () => {
    renderPage({
      'GET /marketplace/favorites': () => Response.json({ items: [chips], next_cursor: null }),
      'GET /marketplace/favorite-states': () => favoriteStates([chips]),
    });

    expect(await screen.findByRole('link', { name: 'Chips' })).toHaveAttribute(
      'href',
      `/marketplace/templates/${chips.id}`,
    );
    expect(screen.getByRole('heading', { level: 1, name: 'Mes favoris' })).toBeInTheDocument();
    expect(document.title).toBe('Mes favoris · TierList');
    expect(
      await screen.findByRole('button', { name: 'Favori « Chips »', pressed: true }),
    ).toBeInTheDocument();
  });

  it('reads the next page of favorites with the cursor', async () => {
    const cursors: (string | null)[] = [];
    renderPage({
      'GET /marketplace/favorites': (request: Request) => {
        const cursor: string | null = new URL(request.url).searchParams.get('cursor');
        cursors.push(cursor);
        return Response.json(
          cursor === null
            ? { items: [chips], next_cursor: 'after-chips' }
            : { items: [sodas], next_cursor: null },
        );
      },
      'GET /marketplace/favorite-states': () => favoriteStates([]),
    });

    fireEvent.click(await screen.findByRole('button', { name: 'Voir plus' }));

    expect(await screen.findByRole('link', { name: 'Sodas' })).toBeInTheDocument();
    expect(cursors).toEqual([null, 'after-chips']);
    expect(screen.queryByRole('button', { name: 'Voir plus' })).not.toBeInTheDocument();
  });

  it('removes a template from the list when it is removed from the favorites', async () => {
    let favorites: MarketplaceTemplate[] = [chips, sodas];
    renderPage({
      'GET /marketplace/favorites': () => Response.json({ items: favorites, next_cursor: null }),
      'GET /marketplace/favorite-states': () => favoriteStates(favorites),
      [`DELETE /marketplace/templates/${chips.id}/favorite`]: () => {
        favorites = [sodas];
        return Response.json({ favorited: false, can_favorite: true });
      },
    });

    fireEvent.click(await screen.findByRole('button', { name: 'Favori « Chips »', pressed: true }));

    await vi.waitFor(() =>
      expect(screen.queryByRole('link', { name: 'Chips' })).not.toBeInTheDocument(),
    );
    expect(screen.getByRole('link', { name: 'Sodas' })).toBeInTheDocument();
  });

  it('invites to browse the public templates when there is no favorite', async () => {
    renderPage({
      'GET /marketplace/favorites': () => Response.json({ items: [], next_cursor: null }),
    });

    expect(await screen.findByText(/Aucun favori pour l'instant/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Parcourir les modèles publics' })).toHaveAttribute(
      'href',
      '/marketplace',
    );
  });

  it('says when the favorites cannot be loaded', async () => {
    renderPage({ 'GET /marketplace/favorites': () => errorResponse(500, 'http_error') });

    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});
