import { fireEvent, screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  closedGameResults,
  closedGameResultsWithoutAbsents,
  RESULTS_TOKEN,
} from '../test/fixtures/results';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { errorResponse, stubBackend } from '../test/stubBackend';
import { ResultsPage } from './ResultsPage';

function renderResultsPage() {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={[`/results/${RESULTS_TOKEN}`]}>
      <Routes>
        <Route path="/results/:token" element={<ResultsPage />} />
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

// Le texte des items de la ligne d'un tier (ou de « Non classés », « Jamais placés »)
function rowItems(label: string): string[] {
  const row: HTMLElement | null = screen.getByText(label, { selector: 'span' }).closest('div');
  if (row === null) throw new Error(`No row ${label}`);
  return within(row)
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
    expect(screen.getByRole('tabpanel')).toHaveAttribute('aria-labelledby', overall.id);
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

  it('says when the results link is unknown', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    stubBackend({ [resultsRoute]: () => errorResponse(404, 'results_not_found') });

    renderResultsPage();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Ce lien de résultats ne correspond à aucune partie terminée.',
    );
  });
});
