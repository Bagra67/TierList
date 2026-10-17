import { fireEvent, screen, within } from '@testing-library/react';
import { type InitialEntry, MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  closedGameResults,
  closedGameResultsWithoutAbsents,
  RESULTS_TOKEN,
} from '../test/fixtures/results';
import type { GameResults } from '../api/results';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { errorResponse, stubBackend } from '../test/stubBackend';
import { ResultsPage } from './ResultsPage';

// La page ouverte par son lien ; state : l'état de navigation posé par le lobby
function renderResultsPage(state?: unknown) {
  const entry: InitialEntry = { pathname: `/results/${RESULTS_TOKEN}`, state };
  return renderWithQueryClient(
    <MemoryRouter initialEntries={[entry]}>
      <Routes>
        <Route path="/results/:token" element={<ResultsPage />} />
        <Route path="/r/:code" element={<h1>Lobby</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

const resultsRoute: string = `GET /results/${RESULTS_TOKEN}`;

// Le faux backend répond selon la case envoyée, et garde les valeurs reçues
function stubResults(): { includeAbsentVotes: string[] } {
  const received: string[] = [];
  stubBackend({
    [resultsRoute]: (request: Request) => {
      const included: string = new URL(request.url).searchParams.get('include_absent_votes') ?? '';
      received.push(included);
      return Response.json(
        included === 'false' ? closedGameResultsWithoutAbsents : closedGameResults,
      );
    },
  });
  return { includeAbsentVotes: received };
}

// Le texte des items de la ligne d'un tier (ou de « Non classés », « Jamais placés ») : chaque
// ligne est un groupe nommé par son tier
function rowItems(label: string): string[] {
  return within(screen.getByRole('group', { name: label }))
    .queryAllByRole('listitem')
    .map((item: HTMLElement) => item.textContent ?? '');
}

// Presse-papiers simulé : jsdom n'en fournit pas
function stubClipboard(writeText: (text: string) => Promise<void>): void {
  Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true });
}

describe('ResultsPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    Reflect.deleteProperty(navigator, 'clipboard');
  });

  it('shows the median ranking by default, with the absent votes included', async () => {
    const { includeAbsentVotes } = stubResults();

    renderResultsPage();

    expect(await screen.findByRole('heading', { name: 'Résultats : Épices' })).toBeInTheDocument();
    expect(screen.getByText(/Partie terminée le/)).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: 'Inclure les votes absents' })).toBeChecked();
    expect(screen.getByRole('tab', { name: 'Médian' })).toHaveAttribute('aria-selected', 'true');
    expect(rowItems('A')).toEqual(['Paprika', 'Chorizo']);
    expect(rowItems('Non classés')).toEqual(['Curry']);
    expect(includeAbsentVotes).toEqual(['true']);
  });

  it('shows the distribution of every item in a table', async () => {
    stubResults();
    renderResultsPage();

    fireEvent.click(await screen.findByRole('tab', { name: 'Global' }));

    const table: HTMLElement = screen.getByRole('table', {
      name: 'Nombre de joueurs qui ont mis chaque item dans chaque tier',
    });
    expect(
      within(table)
        .getAllByRole('columnheader')
        .map((cell: HTMLElement) => cell.textContent),
    ).toEqual(['Item', 'S', 'A', 'Absents']);
    const chorizo: HTMLElement = within(table).getByRole('row', { name: /Chorizo/ });
    expect(
      within(chorizo)
        .getAllByRole('cell')
        .map((cell: HTMLElement) => cell.textContent),
    ).toEqual(['0', '1', '1']);
  });

  it('reads the results again without the absent votes when the box is unchecked', async () => {
    const { includeAbsentVotes } = stubResults();
    renderResultsPage();
    fireEvent.click(await screen.findByRole('tab', { name: 'Global' }));

    fireEvent.click(screen.getByRole('checkbox', { name: 'Inclure les votes absents' }));

    expect(screen.getByRole('checkbox', { name: 'Inclure les votes absents' })).not.toBeChecked();
    await vi.waitFor(() =>
      expect(screen.queryByRole('columnheader', { name: 'Absents' })).not.toBeInTheDocument(),
    );
    expect(includeAbsentVotes).toEqual(['true', 'false']);
  });

  it('shows the ranking of each player and the items they never placed', async () => {
    stubResults();
    renderResultsPage();

    fireEvent.click(await screen.findByRole('tab', { name: 'Par joueur' }));
    expect(rowItems('S')).toEqual(['Paprika']);
    fireEvent.change(screen.getByRole('combobox', { name: 'Joueur' }), { target: { value: '1' } });

    expect(rowItems('A')).toEqual(['Paprika']);
    expect(rowItems('Jamais placés')).toEqual(['Chorizo', 'Curry']);
  });

  it('moves between the views with the arrow keys', async () => {
    stubResults();
    renderResultsPage();
    const median: HTMLElement = await screen.findByRole('tab', { name: 'Médian' });

    fireEvent.keyDown(median, { key: 'ArrowRight' });

    const overall: HTMLElement = screen.getByRole('tab', { name: 'Global' });
    expect(overall).toHaveAttribute('aria-selected', 'true');
    expect(overall).toHaveFocus();
    const panel: HTMLElement = screen.getByRole('tabpanel');
    expect(panel).toHaveAttribute('aria-labelledby', overall.id);
    // Focalisable : la vue n'a pas toujours d'élément interactif
    expect(panel).toHaveAttribute('tabindex', '0');
    fireEvent.keyDown(overall, { key: 'End' });
    expect(screen.getByRole('tab', { name: 'Par joueur' })).toHaveFocus();
  });

  it('copies the public link of the results and announces it', async () => {
    const writeText: (text: string) => Promise<void> = vi.fn(async () => {});
    stubClipboard(writeText);
    stubResults();
    renderResultsPage();

    const link: string = `${window.location.origin}/results/${RESULTS_TOKEN}`;
    expect(await screen.findByRole('textbox', { name: 'Lien public des résultats' })).toHaveValue(
      link,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Copier le lien' }));

    expect(await screen.findByText('Lien copié')).toBeInTheDocument();
    expect(writeText).toHaveBeenCalledWith(link);
  });

  it('asks to copy the public link by hand when the clipboard refuses', async () => {
    stubClipboard(() => Promise.reject(new Error('denied')));
    stubResults();
    renderResultsPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Copier le lien' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Impossible de copier le lien : sélectionnez-le et copiez-le à la main.',
    );
  });

  it('names each item without text by its number, so two images never share a name', async () => {
    const imagesOnly: GameResults = {
      ...closedGameResults,
      items: closedGameResults.items.map((item, index: number) => ({
        ...item,
        text: null,
        image_url: `https://images.example.com/${index}.webp`,
      })),
    };
    stubBackend({ [resultsRoute]: () => Response.json(imagesOnly) });
    renderResultsPage();

    fireEvent.click(await screen.findByRole('tab', { name: 'Global' }));

    expect(
      screen
        .getAllByRole('rowheader')
        .map((header: HTMLElement) => within(header).getByRole('img').getAttribute('alt')),
    ).toEqual(["Image de l'item 1", "Image de l'item 2", "Image de l'item 3"]);
  });

  it('keeps the box and says so when reading the other variant fails', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    stubBackend({
      [resultsRoute]: (request: Request) =>
        new URL(request.url).searchParams.get('include_absent_votes') === 'false'
          ? errorResponse(500, 'internal_error')
          : Response.json(closedGameResults),
    });
    renderResultsPage();
    const box: HTMLElement = await screen.findByRole('checkbox', {
      name: 'Inclure les votes absents',
    });

    fireEvent.click(box);

    // L'erreur prend la place des statistiques, jamais celles de l'autre variante ; une erreur
    // serveur est réessayée une fois avant d'être montrée
    expect(
      await within(screen.getByRole('tabpanel')).findByRole('alert', {}, { timeout: 3000 }),
    ).toBeInTheDocument();
    expect(screen.queryByRole('group', { name: 'A' })).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Résultats : Épices' })).toBeInTheDocument();
    // Recocher remontre tout de suite la variante déjà lue
    fireEvent.click(screen.getByRole('checkbox', { name: 'Inclure les votes absents' }));
    expect(rowItems('A')).toEqual(['Paprika', 'Chorizo']);
  });

  it('links back to the room when opened from its lobby', async () => {
    stubResults();
    renderResultsPage({ roomCode: 'K7P2QX' });

    fireEvent.click(await screen.findByRole('link', { name: 'Retour à la salle' }));

    expect(await screen.findByRole('heading', { name: 'Lobby' })).toBeInTheDocument();
  });

  it('offers no room action: the page is read-only', async () => {
    stubResults();
    renderResultsPage();

    await screen.findByRole('heading', { name: 'Résultats : Épices' });
    // Seuls les onglets et le bouton de copie sont des boutons : ni « Rejouer », ni commande de salle
    expect(
      screen
        .getAllByRole('button')
        .map((button: HTMLElement) => button.textContent)
        .filter((name) => name !== 'Copier le lien'),
    ).toEqual([]);
  });

  it('offers no way back to a room when opened by the public link', async () => {
    stubResults();
    renderResultsPage();

    await screen.findByRole('heading', { name: 'Résultats : Épices' });
    expect(screen.queryByRole('link', { name: 'Retour à la salle' })).not.toBeInTheDocument();
  });

  it('says when the results link is unknown', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    stubBackend({ [resultsRoute]: () => errorResponse(404, 'results_not_found') });

    renderResultsPage();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Ce lien de résultats ne correspond à aucune partie terminée.',
    );
  });
});
