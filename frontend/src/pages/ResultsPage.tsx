import { type ChangeEvent, useState } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';
import { type Location, type Params, useLocation, useParams } from 'react-router';

import { type GameResults, type GameResultsState, useGameResults } from '../api/results';
import type { ItemDistribution } from '../api/results';
import type { GameItem } from '../api/rooms';
import { CopyLinkField } from '../components/CopyLinkField';
import { ErrorMessage } from '../components/ErrorMessage';
import { ItemVotesPanel } from '../components/ItemVotesPanel';
import { ResultsDistributionTable } from '../components/ResultsDistributionTable';
import { ResultsPlayerView } from '../components/ResultsPlayerView';
import { ResultsRoomActions } from '../components/ResultsRoomActions';
import { ResultsTabs } from '../components/ResultsTabs';
import { ResultsTierList } from '../components/ResultsTierList';
import {
  type ItemSelection,
  type ResultItem,
  type ResultItems,
  type ResultsView,
  resultsPanelId,
  resultsTabId,
} from '../components/resultsViews';
import { isResultsLinkState, type ResultsLinkState, resultsPath } from '../constants/routes';
import { translateError } from '../errors/apiError';
import { LoadingSkeleton } from '../components/LoadingSkeleton';

// Résultats d'une partie close (US-5.2), ouverts par leur lien, avec ou sans compte (US-5.3) :
// classement médian, vue globale et classement de chaque joueur, avec ou sans les votes absents,
// et le lien public à copier. Lecture seule : la partie close ne change plus, et la page n'offre
// aucune action de salle (seulement le retour à la salle, et rejouer pour le room admin, quand on
// vient de son lobby)
export function ResultsPage() {
  // Toujours présent : la route RESULTS déclare ce paramètre
  const { token = '' }: Readonly<Params> = useParams();
  const location: Location = useLocation();
  const [includeAbsentVotes, setIncludeAbsentVotes] = useState<boolean>(true);
  const [view, setView] = useState<ResultsView>('median');
  // Élément dont les votes sont affichés ; par défaut le premier du modèle
  const [chosenItemId, setChosenItemId] = useState<string | null>(null);
  const state: GameResultsState = useGameResults(token, includeAbsentVotes);
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  // Venu du lobby d'une salle : un lien y ramène, et le room admin peut rejouer
  const fromRoom: ResultsLinkState | null = isResultsLinkState(location.state)
    ? location.state
    : null;

  // Rien de lu encore : chargement, ou échec de la première lecture
  if (state.anyVariant === undefined) {
    return (
      <main className="mx-auto flex w-full max-w-5xl flex-col items-start gap-6 px-4 py-10">
        {state.error === null ? (
          <LoadingSkeleton shape="board" />
        ) : (
          <ErrorMessage>{translateError(t, state.error)}</ErrorMessage>
        )}
      </main>
    );
  }

  const known: GameResults = state.anyVariant;
  const items: ResultItems = new Map(
    known.items.map((item: GameItem, index: number): [string, ResultItem] => {
      const imageLabel: string = t('results.itemImage', { number: index + 1 });
      return [item.id, { item, imageLabel, name: item.text ?? imageLabel }];
    }),
  );

  // La vue montre des items, donc des boutons
  const panelHasItems: boolean =
    state.results !== undefined &&
    known.items.length > 0 &&
    !(view === 'players' && state.results.players.length === 0);

  const selection: ItemSelection = {
    selectedItemId: chosenItemId ?? known.items[0]?.id ?? null,
    onSelect: setChosenItemId,
  };
  const selectedItem: ResultItem | undefined =
    selection.selectedItemId === null ? undefined : items.get(selection.selectedItemId);
  const selectedDistribution: ItemDistribution | undefined = state.results?.distribution.find(
    (entry: ItemDistribution) => entry.item_id === selection.selectedItemId,
  );

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col items-start gap-6 px-4 py-10">
      {fromRoom !== null && <ResultsRoomActions fromRoom={fromRoom} />}
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold">
          {t('results.title', { name: known.template_name })}
        </h1>
        <p className="text-muted-foreground">
          {t('results.closedAt', { date: new Date(known.closed_at) })}
        </p>
      </div>
      {/* Le lien de cette page, sur l'adresse de l'application : il marche sans compte, et après
          la fermeture de la salle (US-5.3) */}
      <CopyLinkField
        label={t('results.publicLink')}
        link={`${window.location.origin}${resultsPath(token)}`}
      />
      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={includeAbsentVotes}
          onChange={(event: ChangeEvent<HTMLInputElement>) =>
            setIncludeAbsentVotes(event.target.checked)
          }
        />
        {t('results.includeAbsentVotes')}
      </label>
      {/* Sur grand écran, les votes de l'élément choisi à droite de la vue (ItemVotesPanel) */}
      <div className="grid w-full items-start gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="flex min-w-0 flex-col gap-4">
          <ResultsTabs selected={view} onSelect={setView} />
          {/* Motif ARIA tabs : le panneau n'est focalisable que s'il n'a aucun élément interactif
              (chargement, erreur, partie sans joueur) ; sinon ses items, des boutons, suffisent */}
          <div
            role="tabpanel"
            id={resultsPanelId(view)}
            aria-labelledby={resultsTabId(view)}
            aria-busy={state.isPending}
            tabIndex={panelHasItems ? undefined : 0}
            className="w-full rounded-xl outline-none focus-visible:ring-3 focus-visible:ring-ring"
          >
            {/* Les statistiques montrées correspondent toujours à la case : pendant une lecture ou
              après un échec, rien d'autre que l'état n'est affiché */}
            {state.results !== undefined ? (
              <ResultsViewContent
                view={view}
                results={state.results}
                items={items}
                selection={selection}
              />
            ) : state.error !== null ? (
              <ErrorMessage>{translateError(t, state.error)}</ErrorMessage>
            ) : (
              <LoadingSkeleton shape="board" />
            )}
          </div>
        </div>
        {state.results !== undefined &&
          selectedItem !== undefined &&
          selectedDistribution !== undefined && (
            <ItemVotesPanel
              tiers={state.results.tiers}
              resultItem={selectedItem}
              distribution={selectedDistribution}
              playerNames={state.results.players.map((player) => player.display_name)}
              includeAbsentVotes={state.results.include_absent_votes}
            />
          )}
      </div>
    </main>
  );
}

interface ResultsViewContentProps {
  view: ResultsView;
  results: GameResults;
  items: ResultItems;
  selection: ItemSelection;
}

function ResultsViewContent({ view, results, items, selection }: ResultsViewContentProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();

  if (view === 'median') {
    return (
      <ResultsTierList
        tiers={results.tiers}
        rows={results.median_ranking}
        items={items}
        extraRow={{ label: t('results.median.unranked'), itemIds: results.unranked_item_ids }}
        selection={selection}
      />
    );
  }
  if (view === 'overall') {
    return (
      <ResultsDistributionTable
        tiers={results.tiers}
        items={items}
        distribution={results.distribution}
        includeAbsentVotes={results.include_absent_votes}
        selection={selection}
      />
    );
  }
  return (
    <ResultsPlayerView
      tiers={results.tiers}
      players={results.players}
      items={items}
      selection={selection}
    />
  );
}
