import { type ChangeEvent, useState } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';
import { type Location, type Params, Link, useLocation, useParams } from 'react-router';

import { type GameResults, type GameResultsState, useGameResults } from '../api/results';
import type { GameItem } from '../api/rooms';
import { CopyLinkField } from '../components/CopyLinkField';
import { ErrorMessage } from '../components/ErrorMessage';
import { ResultsDistributionTable } from '../components/ResultsDistributionTable';
import { ResultsPlayerView } from '../components/ResultsPlayerView';
import { ResultsTabs } from '../components/ResultsTabs';
import { ResultsTierList } from '../components/ResultsTierList';
import {
  type ResultItem,
  type ResultItems,
  type ResultsView,
  resultsPanelId,
  resultsTabId,
} from '../components/resultsViews';
import { isResultsLinkState, resultsPath, roomPath } from '../constants/routes';
import { translateError } from '../errors/apiError';

// Résultats d'une partie close (US-5.2), ouverts par leur lien, avec ou sans compte (US-5.3) :
// classement médian, vue globale et classement de chaque joueur, avec ou sans les votes absents,
// et le lien public à copier. Lecture seule : la partie close ne change plus, et la page n'offre
// aucune action de salle (seulement le retour à la salle quand on vient de son lobby)
export function ResultsPage() {
  // Toujours présent : la route RESULTS déclare ce paramètre
  const { token = '' }: Readonly<Params> = useParams();
  const location: Location = useLocation();
  const [includeAbsentVotes, setIncludeAbsentVotes] = useState<boolean>(true);
  const [view, setView] = useState<ResultsView>('median');
  const state: GameResultsState = useGameResults(token, includeAbsentVotes);
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  // Venu du lobby d'une salle : un lien y ramène
  const roomCode: string | null = isResultsLinkState(location.state)
    ? location.state.roomCode
    : null;

  // Rien de lu encore : chargement, ou échec de la première lecture
  if (state.anyVariant === undefined) {
    return (
      <main className="mx-auto flex w-full max-w-3xl flex-col items-start gap-6 px-4 py-10">
        {state.error === null ? (
          <p className="text-muted-foreground">{t('common.loading')}</p>
        ) : (
          <ErrorMessage>{translateError(t, state.error)}</ErrorMessage>
        )}
      </main>
    );
  }

  const known: GameResults = state.anyVariant;
  const items: ResultItems = new Map(
    known.items.map((item: GameItem, index: number): [string, ResultItem] => [
      item.id,
      { item, imageLabel: t('results.itemImage', { number: index + 1 }) },
    ]),
  );

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col items-start gap-6 px-4 py-10">
      {roomCode !== null && (
        <Link
          to={roomPath(roomCode)}
          className="text-sm font-medium text-primary underline-offset-4 hover:underline"
        >
          {t('results.backToRoom')}
        </Link>
      )}
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
      <div className="flex w-full flex-col gap-4">
        <ResultsTabs selected={view} onSelect={setView} />
        {/* Focalisable : la plupart des vues n'ont aucun élément interactif (motif ARIA tabs) */}
        <div
          role="tabpanel"
          id={resultsPanelId(view)}
          aria-labelledby={resultsTabId(view)}
          aria-busy={state.isPending}
          tabIndex={0}
          className="w-full rounded-xl outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          {/* Les statistiques montrées correspondent toujours à la case : pendant une lecture ou
              après un échec, rien d'autre que l'état n'est affiché */}
          {state.results !== undefined ? (
            <ResultsViewContent view={view} results={state.results} items={items} />
          ) : state.error !== null ? (
            <ErrorMessage>{translateError(t, state.error)}</ErrorMessage>
          ) : (
            <p className="text-muted-foreground">{t('common.loading')}</p>
          )}
        </div>
      </div>
    </main>
  );
}

interface ResultsViewContentProps {
  view: ResultsView;
  results: GameResults;
  items: ResultItems;
}

function ResultsViewContent({ view, results, items }: ResultsViewContentProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();

  if (view === 'median') {
    return (
      <ResultsTierList
        tiers={results.tiers}
        rows={results.median_ranking}
        items={items}
        extraRow={{ label: t('results.median.unranked'), itemIds: results.unranked_item_ids }}
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
      />
    );
  }
  return <ResultsPlayerView tiers={results.tiers} players={results.players} items={items} />;
}
