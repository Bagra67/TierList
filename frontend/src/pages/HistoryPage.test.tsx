import { fireEvent, screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { HistoryPage as HistoryPageData } from '../api/history';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { errorResponse, stubBackend } from '../test/stubBackend';
import { HistoryPage } from './HistoryPage';

function renderHistoryPage() {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={['/history']}>
      <Routes>
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/results/:token" element={<h1>Résultats</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

const firstPage: HistoryPageData = {
  games: [
    {
      public_token: 'spices-token',
      template_name: 'Épices',
      closed_at: '2026-10-17T18:30:00Z',
      player_count: 3,
    },
    {
      public_token: 'cheese-token',
      template_name: 'Fromages',
      closed_at: '2026-10-16T20:00:00Z',
      player_count: 1,
    },
  ],
  has_more: true,
};

const secondPage: HistoryPageData = {
  games: [
    {
      public_token: 'fruit-token',
      template_name: 'Fruits',
      closed_at: '2026-10-10T12:00:00Z',
      player_count: 2,
    },
  ],
  has_more: false,
};

// Le faux backend répond selon l'offset demandé, et garde les offsets reçus
function stubHistory(): string[] {
  const offsets: string[] = [];
  stubBackend({
    'GET /history': (request: Request) => {
      const offset: string = new URL(request.url).searchParams.get('offset') ?? '';
      offsets.push(offset);
      return Response.json(offset === '0' ? firstPage : secondPage);
    },
  });
  return offsets;
}

describe('HistoryPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('lists the closed games with their template, date, players and results link', async () => {
    stubHistory();
    renderHistoryPage();

    const list: HTMLElement = await screen.findByRole('list');
    const rows: HTMLElement[] = within(list).getAllByRole('listitem');
    expect(rows).toHaveLength(2);
    expect(within(rows[0]).getByText('Épices')).toBeInTheDocument();
    expect(within(rows[0]).getByText('3 joueurs')).toBeInTheDocument();
    expect(within(rows[1]).getByText('1 joueur')).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: 'Voir les résultats de la partie Épices' }),
    ).toHaveAttribute('href', '/results/spices-token');
  });

  it('opens the results of a game', async () => {
    stubHistory();
    renderHistoryPage();

    fireEvent.click(
      await screen.findByRole('link', { name: 'Voir les résultats de la partie Fromages' }),
    );

    expect(await screen.findByRole('heading', { name: 'Résultats' })).toBeInTheDocument();
  });

  it('reads the next page after the games already shown', async () => {
    const offsets: string[] = stubHistory();
    renderHistoryPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Voir plus' }));

    expect(await screen.findByText('Fruits')).toBeInTheDocument();
    expect(screen.getAllByRole('listitem')).toHaveLength(3);
    // La page suivante commence après les 2 parties déjà lues ; plus rien ensuite
    expect(offsets).toEqual(['0', '2']);
    expect(screen.queryByRole('button', { name: 'Voir plus' })).not.toBeInTheDocument();
  });

  it('says when there is no game yet', async () => {
    stubBackend({ 'GET /history': () => Response.json({ games: [], has_more: false }) });

    renderHistoryPage();

    expect(
      await screen.findByText(
        "Aucune partie terminée pour l'instant. Vos parties apparaîtront ici une fois closes.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByRole('list')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Créer ou rejoindre une partie' })).toHaveAttribute(
      'href',
      '/',
    );
  });

  it('says why the history cannot be read', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    stubBackend({ 'GET /history': () => errorResponse(500, 'internal_error') });

    renderHistoryPage();

    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});
