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
import { aliceRoomInGame } from '../test/fixtures/rooms';
import { calledRoutes, errorResponse, stubBackend } from '../test/stubBackend';
import type { ResultsLinkState } from '../constants/routes';
import { ResultsPage } from './ResultsPage';

function renderResultsPage(stateFromLobby?: ResultsLinkState) {
  const entry: InitialEntry = { pathname: `/results/${RESULTS_TOKEN}`, state: stateFromLobby };
  return renderWithQueryClient(
    <MemoryRouter initialEntries={[entry]}>
      <Routes>
        <Route path="/results/:token" element={<ResultsPage />} />
        <Route path="/r/:code" element={<h1>Lobby</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

const ANIMATION_END_EVENT_HEARD_BY_REACT_IN_JSDOM: string = 'webkitAnimationEnd';
const resultsRoute: string = `GET /results/${RESULTS_TOKEN}`;

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

function rowItems(label: string): string[] {
  return within(screen.getByRole('group', { name: label }))
    .queryAllByRole('listitem')
    .map((item: HTMLElement) => item.textContent ?? '');
}

function voteLines(item: string): string[] {
  return within(screen.getByRole('region', { name: `Votes : ${item}` }))
    .getAllByRole('listitem')
    .map((line: HTMLElement) => line.textContent ?? '');
}

function fireAnimationEnd(element: HTMLElement): void {
  fireEvent(element, new Event(ANIMATION_END_EVENT_HEARD_BY_REACT_IN_JSDOM, { bubbles: true }));
}

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
      name: 'Nombre de joueurs qui ont mis chaque élément dans chaque tier',
    });
    expect(
      within(table)
        .getAllByRole('columnheader')
        .map((cell: HTMLElement) => cell.textContent),
    ).toEqual(['Élément', 'S', 'A', 'Absents']);
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

  it('reveals the tiers one by one, from the bottom, when the results open', async () => {
    stubResults();
    renderResultsPage();

    const tierS: HTMLElement = await screen.findByRole('group', { name: 'S' });
    expect(tierS).toHaveClass('motion-safe:animate-reveal');
    expect(tierS).toHaveStyle({ animationDelay: '520ms' });
    expect(screen.getByRole('group', { name: 'A' })).toHaveStyle({ animationDelay: '260ms' });
    expect(screen.getByRole('group', { name: 'Non classés' })).toHaveStyle({
      animationDelay: '0ms',
    });
  });

  it('does not reveal a view again when coming back to it, unless asked', async () => {
    stubResults();
    renderResultsPage();
    await screen.findByRole('group', { name: 'S' });

    fireEvent.click(screen.getByRole('tab', { name: 'Global' }));
    expect(screen.queryByRole('button', { name: 'Rejouer la révélation' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('tab', { name: 'Médian' }));
    expect(screen.getByRole('group', { name: 'S' })).not.toHaveClass('motion-safe:animate-reveal');

    fireEvent.click(screen.getByRole('button', { name: 'Rejouer la révélation' }));
    expect(screen.getByRole('group', { name: 'S' })).toHaveClass('motion-safe:animate-reveal');
  });

  it('keeps the chosen player when the reveal is replayed', async () => {
    stubResults();
    renderResultsPage();
    fireEvent.click(await screen.findByRole('tab', { name: 'Par joueur' }));
    fireEvent.change(screen.getByRole('combobox', { name: 'Joueur' }), { target: { value: '1' } });

    fireEvent.click(screen.getByRole('button', { name: 'Rejouer la révélation' }));

    expect(screen.getByRole('combobox', { name: 'Joueur' })).toHaveValue('1');
    expect(screen.getByRole('group', { name: 'S' })).toHaveClass('motion-safe:animate-reveal');
  });

  it('stops the reveal once the top row has appeared: a row added later is not animated', async () => {
    stubResults();
    renderResultsPage();
    fireEvent.click(await screen.findByRole('tab', { name: 'Par joueur' }));
    const tierS: HTMLElement = screen.getByRole('group', { name: 'S' });

    fireAnimationEnd(within(tierS).getAllByRole('listitem')[0]);
    expect(tierS).toHaveClass('motion-safe:animate-reveal');

    fireAnimationEnd(tierS);
    fireEvent.change(screen.getByRole('combobox', { name: 'Joueur' }), { target: { value: '1' } });

    expect(screen.getByRole('group', { name: 'Jamais placés' })).not.toHaveClass(
      'motion-safe:animate-reveal',
    );
  });

  it('does not reveal again when the absent votes box is toggled', async () => {
    stubResults();
    renderResultsPage();
    await screen.findByRole('group', { name: 'S' });

    fireEvent.click(screen.getByRole('checkbox', { name: 'Inclure les votes absents' }));
    expect(screen.queryByRole('button', { name: 'Rejouer la révélation' })).not.toBeInTheDocument();

    expect(await screen.findByRole('group', { name: 'S' })).not.toHaveClass(
      'motion-safe:animate-reveal',
    );
  });

  it('shows the votes of the first item by default, with the players', async () => {
    stubResults();
    renderResultsPage();

    await screen.findByRole('region', { name: 'Votes : Paprika' });
    expect(voteLines('Paprika')).toEqual(['S1 voteAlice', 'A1 voteLou', 'Absents0 vote']);
  });

  it('shows the votes of the item clicked in a view', async () => {
    stubResults();
    renderResultsPage();
    const chorizo: HTMLElement = await screen.findByRole('button', {
      name: 'Voir les votes : Chorizo',
    });
    expect(chorizo).not.toHaveAttribute('aria-current');

    fireEvent.click(chorizo);

    expect(chorizo).toHaveAttribute('aria-current', 'true');
    expect(voteLines('Chorizo')).toEqual(['S0 vote', 'A1 voteAlice', 'Absents1 voteLou']);
    fireEvent.click(screen.getByRole('tab', { name: 'Global' }));
    expect(screen.getByRole('region', { name: 'Votes : Chorizo' })).toBeInTheDocument();
  });

  it('leaves the absent players out of the votes without the absent votes', async () => {
    stubResults();
    renderResultsPage();
    await screen.findByRole('region', { name: 'Votes : Paprika' });

    fireEvent.click(screen.getByRole('checkbox', { name: 'Inclure les votes absents' }));

    await vi.waitFor(() => expect(voteLines('Paprika')).toEqual(['S1 vote', 'A0 vote']));
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
    fireEvent.keyDown(overall, { key: 'End' });
    expect(screen.getByRole('tab', { name: 'Par joueur' })).toHaveFocus();
  });

  it('leaves out of the tab order a panel whose items are buttons', async () => {
    stubResults();
    renderResultsPage();

    expect(await screen.findByRole('tabpanel')).not.toHaveAttribute('tabindex');

    fireEvent.click(screen.getByRole('tab', { name: 'Global' }));
    expect(screen.getByRole('tabpanel')).not.toHaveAttribute('tabindex');
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
    ).toEqual(["Image de l'élément 1", "Image de l'élément 2", "Image de l'élément 3"]);
  });

  it('shows an image removed by the moderation instead of the image', async () => {
    const removedImage: GameResults = {
      ...closedGameResults,
      items: closedGameResults.items.map((item, index: number) =>
        index === 0 ? { ...item, text: null, image_url: null, image_removed: true } : item,
      ),
    };
    stubBackend({ [resultsRoute]: () => Response.json(removedImage) });
    renderResultsPage();

    fireEvent.click(await screen.findByRole('tab', { name: 'Global' }));

    const [firstHeader] = screen.getAllByRole('rowheader');
    expect(within(firstHeader).getByRole('img', { name: 'Image retirée' })).toBeInTheDocument();
    expect(firstHeader.querySelector('img')).toBeNull();
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

    expect(await within(screen.getByRole('tabpanel')).findByRole('alert')).toBeInTheDocument();
    expect(screen.queryByRole('group', { name: 'A' })).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Résultats : Épices' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('checkbox', { name: 'Inclure les votes absents' }));
    expect(rowItems('A')).toEqual(['Paprika', 'Chorizo']);
  });

  it('links back to the room when opened from its lobby', async () => {
    stubResults();
    renderResultsPage({ roomCode: 'K7P2QX', isAdmin: false });

    fireEvent.click(await screen.findByRole('link', { name: 'Retour à la salle' }));

    expect(await screen.findByRole('heading', { name: 'Lobby' })).toBeInTheDocument();
  });

  it('lets the room admin play again from the results, then opens the room', async () => {
    const fetchMock = stubBackend({
      [resultsRoute]: () => Response.json(closedGameResults),
      'POST /rooms/K7P2QX/game': () => Response.json(aliceRoomInGame, { status: 201 }),
    });
    renderResultsPage({ roomCode: 'K7P2QX', isAdmin: true });

    fireEvent.click(await screen.findByRole('button', { name: 'Rejouer' }));

    expect(await screen.findByRole('heading', { name: 'Lobby' })).toBeInTheDocument();
    expect(calledRoutes(fetchMock)).toContain('POST /rooms/K7P2QX/game');
  });

  it('says why playing again failed, and stays on the results', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    stubBackend({
      [resultsRoute]: () => Response.json(closedGameResults),
      'POST /rooms/K7P2QX/game': () => errorResponse(409, 'game_in_progress'),
    });
    renderResultsPage({ roomCode: 'K7P2QX', isAdmin: true });

    fireEvent.click(await screen.findByRole('button', { name: 'Rejouer' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/partie est déjà en cours/i);
    expect(screen.getByRole('heading', { name: 'Résultats : Épices' })).toBeInTheDocument();
  });

  it('does not offer to play again to a participant who is not the room admin', async () => {
    stubResults();
    renderResultsPage({ roomCode: 'K7P2QX', isAdmin: false });

    await screen.findByRole('link', { name: 'Retour à la salle' });
    expect(screen.queryByRole('button', { name: 'Rejouer' })).not.toBeInTheDocument();
  });

  it('offers no room action: the page is read-only', async () => {
    stubResults();
    renderResultsPage();

    await screen.findByRole('heading', { name: 'Résultats : Épices' });
    expect(
      screen
        .getAllByRole('button')
        .filter(
          (button: HTMLElement) =>
            button.textContent !== 'Copier le lien' &&
            button.textContent !== 'Rejouer la révélation' &&
            button.textContent !== 'Signaler' &&
            !(button.getAttribute('aria-label') ?? '').startsWith('Voir les votes : '),
        ),
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

  it('reports the game and the chosen player, even for a visitor', async () => {
    stubResults();
    renderResultsPage();

    expect(await screen.findByRole('button', { name: 'Signaler : Épices' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('tab', { name: 'Par joueur' }));
    expect(screen.getByRole('button', { name: 'Signaler : Alice' })).toBeInTheDocument();
  });

  it('reports the image of the chosen item, not a text nor a removed image', async () => {
    const [paprika, chorizo, curry]: GameResults['items'] = closedGameResults.items;
    stubBackend({
      [resultsRoute]: () =>
        Response.json({
          ...closedGameResults,
          items: [
            { ...paprika, image_url: 'https://images.example.com/paprika.webp', text: null },
            { ...chorizo, image_removed: true, text: null },
            curry,
          ],
        }),
    });
    renderResultsPage();

    expect(
      await screen.findByRole('button', { name: "Signaler : Image de l'élément 1" }),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: "Voir les votes : Image de l'élément 2" }));
    expect(
      screen.queryByRole('button', { name: /^Signaler : Image de l'élément/ }),
    ).not.toBeInTheDocument();
  });
});
