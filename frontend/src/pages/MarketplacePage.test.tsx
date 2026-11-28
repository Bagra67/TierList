import { fireEvent, screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { MarketplaceTemplate } from '../api/marketplace';
import { marketplaceCard } from '../test/fixtures/marketplace';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { calledRoutes, type StubbedRoute, signedInSession, stubBackend } from '../test/stubBackend';
import { MarketplacePage } from './MarketplacePage';

const chips = marketplaceCard('5d0c2a8e-1f3b-4c7a-9e21-3a4b5c6d7e01', 'Chips');
const sodas = marketplaceCard('5d0c2a8e-1f3b-4c7a-9e21-3a4b5c6d7e02', 'Sodas', { like_count: 1 });

interface StubbedList {
  searches: URLSearchParams[];
}

function stubMarketplace(
  pageFor: (params: URLSearchParams) => {
    items: MarketplaceTemplate[];
    next_cursor: string | null;
  },
  tags: string[] = ['Apéro', 'Films'],
  otherRoutes: Record<string, StubbedRoute> = {},
): StubbedList {
  const searches: URLSearchParams[] = [];
  stubBackend({
    ...otherRoutes,
    'GET /marketplace/templates': (request: Request) => {
      const params: URLSearchParams = new URL(request.url).searchParams;
      searches.push(params);
      return Response.json(pageFor(params));
    },
    'GET /marketplace/tags': () => Response.json({ tags }),
  });
  return { searches };
}

function renderPage(path: string = '/marketplace') {
  renderWithQueryClient(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/marketplace" element={<MarketplacePage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('MarketplacePage', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('shows the public templates as cards, the most liked first by default', async () => {
    const { searches } = stubMarketplace(() => ({ items: [chips, sodas], next_cursor: null }));

    renderPage();

    const link: HTMLElement = await screen.findByRole('link', { name: 'Chips' });
    expect(link).toHaveAttribute('href', `/marketplace/templates/${chips.id}`);
    expect(screen.getAllByText('par Camille · 8 éléments')).toHaveLength(2);
    expect(screen.getByText("3 j'aime")).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'Trier par' })).toHaveValue('popular');
    expect(searches[0].get('sort')).toBe('popular');
    expect(document.title).toBe('Modèles publics · TierList');
  });

  it('shows the TierList picks in their own row above the list, without a search', async () => {
    const pick: MarketplaceTemplate = marketplaceCard('pick-id', 'Jeux de société', {
      owner_name: 'TierList',
      featured: true,
    });
    stubMarketplace(() => ({ items: [pick, chips], next_cursor: null }), undefined, {
      'GET /marketplace/featured': () => Response.json({ items: [pick] }),
    });

    renderPage();

    const picks: HTMLElement = await screen.findByRole('region', { name: 'Sélection TierList' });
    expect(within(picks).getByRole('link', { name: 'Jeux de société' })).toBeInTheDocument();
    expect(within(picks).queryByText('Sélection TierList', { selector: 'span' })).toBeNull();
    expect(screen.getAllByText('Sélection TierList', { selector: 'span' })).toHaveLength(1);
  });

  it('hides the TierList picks during a search', async () => {
    const pick: MarketplaceTemplate = marketplaceCard('pick-id', 'Jeux de société', {
      featured: true,
    });
    stubMarketplace(() => ({ items: [chips], next_cursor: null }), undefined, {
      'GET /marketplace/featured': () => Response.json({ items: [pick] }),
    });

    renderPage('/marketplace?q=chips');

    await screen.findByRole('link', { name: 'Chips' });
    expect(screen.queryByRole('region', { name: 'Sélection TierList' })).not.toBeInTheDocument();
  });

  it('searches with the typed keywords', async () => {
    const { searches } = stubMarketplace(() => ({ items: [chips], next_cursor: null }));
    renderPage();

    fireEvent.change(await screen.findByRole('searchbox', { name: 'Rechercher un modèle' }), {
      target: { value: '  chip  ' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Rechercher' }));

    await vi.waitFor(() => expect(searches.at(-1)?.get('q')).toBe('chip'));
  });

  it('filters on a popular tag, and clicking it again removes the filter', async () => {
    const { searches } = stubMarketplace(() => ({ items: [chips], next_cursor: null }));
    renderPage();

    const tags: HTMLElement = await screen.findByRole('list', { name: 'Étiquettes populaires' });
    const films: HTMLElement = within(tags).getByRole('button', { name: 'Films' });
    fireEvent.click(films);

    await vi.waitFor(() => expect(searches.at(-1)?.get('tag')).toBe('Films'));
    expect(within(tags).getByRole('button', { name: 'Films' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    fireEvent.click(within(tags).getByRole('button', { name: 'Films' }));
    await vi.waitFor(() => expect(searches.at(-1)?.has('tag')).toBe(false));
  });

  it('sorts by the newest', async () => {
    const { searches } = stubMarketplace(() => ({ items: [chips], next_cursor: null }));
    renderPage();

    fireEvent.change(await screen.findByRole('combobox', { name: 'Trier par' }), {
      target: { value: 'newest' },
    });

    await vi.waitFor(() => expect(searches.at(-1)?.get('sort')).toBe('newest'));
  });

  it('reads the next page without showing a template twice', async () => {
    const { searches } = stubMarketplace((params: URLSearchParams) =>
      params.get('cursor') === null
        ? { items: [chips], next_cursor: 'second-page' }
        : { items: [chips, sodas], next_cursor: null },
    );
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Voir plus' }));

    expect(await screen.findByRole('link', { name: 'Sodas' })).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: 'Chips' })).toHaveLength(1);
    expect(searches.at(-1)?.get('cursor')).toBe('second-page');
    expect(screen.queryByRole('button', { name: 'Voir plus' })).not.toBeInTheDocument();
  });

  it('says that nothing matches and offers to clear the search', async () => {
    const { searches } = stubMarketplace(() => ({ items: [], next_cursor: null }));
    renderPage('/marketplace?q=zzz');

    expect(
      await screen.findByText('Aucun modèle public ne correspond à votre recherche.'),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Effacer la recherche' }));

    await vi.waitFor(() => expect(searches.at(-1)?.has('q')).toBe(false));
  });

  it('says that there is no public template yet', async () => {
    stubMarketplace(() => ({ items: [], next_cursor: null }), []);
    renderPage();

    expect(await screen.findByText("Aucun modèle public pour l'instant.")).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Effacer la recherche' })).not.toBeInTheDocument();
  });

  it('shows the image of the first item as the preview', async () => {
    stubMarketplace(() => ({
      items: [
        marketplaceCard(chips.id, 'Photos', {
          preview_image_url: 'https://images.example.com/a.webp',
        }),
      ],
      next_cursor: null,
    }));
    renderPage();

    await screen.findByRole('link', { name: 'Photos' });
    expect(document.querySelector('img')).toHaveAttribute(
      'src',
      'https://images.example.com/a.webp',
    );
  });

  it('shows on the cards which templates the signed-in reader likes, and likes from a card', async () => {
    const liked: string[] = [];
    stubMarketplace(() => ({ items: [chips, sodas], next_cursor: null }), [], {
      ...signedInSession,
      'GET /marketplace/likes': () =>
        Response.json({
          items: [
            { template_id: chips.id, liked: true, like_count: 3, can_like: true },
            { template_id: sodas.id, liked: false, like_count: 1, can_like: true },
          ],
        }),
      [`PUT /marketplace/templates/${sodas.id}/like`]: () => {
        liked.push(sodas.id);
        return Response.json({ liked: true, like_count: 2, can_like: true });
      },
    });
    renderPage();

    expect(
      await screen.findByRole('button', { name: "J'aime « Chips » · 3", pressed: true }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: "J'aime « Sodas » · 1", pressed: false }));

    expect(
      await screen.findByRole('button', { name: "J'aime « Sodas » · 2", pressed: true }),
    ).toBeInTheDocument();
    expect(liked).toEqual([sodas.id]);
  });

  it('shows only the count on the cards of templates the reader may not like', async () => {
    stubMarketplace(() => ({ items: [chips], next_cursor: null }), [], {
      ...signedInSession,
      'GET /marketplace/likes': () =>
        Response.json({
          items: [{ template_id: chips.id, liked: false, like_count: 3, can_like: false }],
        }),
    });
    renderPage();

    expect(await screen.findByText("3 j'aime")).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /J'aime/ })).not.toBeInTheDocument();
  });

  it('asks no like state for a visitor, who sees the counts only', async () => {
    stubMarketplace(() => ({ items: [chips], next_cursor: null }));
    const backend = vi.mocked(fetch);
    renderPage();

    expect(await screen.findByText("3 j'aime")).toBeInTheDocument();
    expect(calledRoutes(backend)).not.toContain('GET /marketplace/likes');
    expect(screen.queryByRole('button', { name: /J'aime/ })).not.toBeInTheDocument();
  });

  it('shows on the cards which templates are in the favorites, and adds one from a card', async () => {
    const favorited: string[] = [];
    stubMarketplace(() => ({ items: [chips, sodas], next_cursor: null }), [], {
      ...signedInSession,
      'GET /marketplace/favorite-states': () =>
        Response.json({
          items: [
            { template_id: chips.id, favorited: true, can_favorite: true },
            { template_id: sodas.id, favorited: false, can_favorite: true },
          ],
        }),
      [`PUT /marketplace/templates/${sodas.id}/favorite`]: () => {
        favorited.push(sodas.id);
        return Response.json({ favorited: true, can_favorite: true });
      },
    });
    renderPage();

    expect(
      await screen.findByRole('button', { name: 'Favori « Chips »', pressed: true }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Favori « Sodas »', pressed: false }));

    expect(
      await screen.findByRole('button', { name: 'Favori « Sodas »', pressed: true }),
    ).toBeInTheDocument();
    expect(favorited).toEqual([sodas.id]);
  });

  it('asks no favorite state for a visitor, who sees no favorite button', async () => {
    stubMarketplace(() => ({ items: [chips], next_cursor: null }));
    const backend = vi.mocked(fetch);
    renderPage();

    expect(await screen.findByText("3 j'aime")).toBeInTheDocument();
    expect(calledRoutes(backend)).not.toContain('GET /marketplace/favorite-states');
    expect(screen.queryByRole('button', { name: /Favori/ })).not.toBeInTheDocument();
  });

  it('names on a card the template it was copied from', async () => {
    const copy = marketplaceCard('5d0c2a8e-1f3b-4c7a-9e21-3a4b5c6d7e03', 'Chips du monde', {
      copied_from: { template_id: chips.id, name: 'Chips', owner_name: 'Noé' },
    });
    stubMarketplace(() => ({ items: [copy], next_cursor: null }));
    renderPage();

    expect(await screen.findByRole('link', { name: '« Chips »' })).toHaveAttribute(
      'href',
      `/marketplace/templates/${chips.id}`,
    );
    expect(screen.getByText(/copié depuis/)).toHaveTextContent('copié depuis « Chips » par Noé');
  });
});
