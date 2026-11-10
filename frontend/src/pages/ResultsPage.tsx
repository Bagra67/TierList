import { type ChangeEvent, useCallback, useState } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';
import { type Location, type Params, useLocation, useParams } from 'react-router';

import { type GameResults, type GameResultsState, useGameResults } from '../api/results';
import type { ItemDistribution } from '../api/results';
import type { GameItem } from '../api/rooms';
import { CopyLinkField } from '../components/CopyLinkField';
import { ErrorMessage } from '../components/ErrorMessage';
import { ItemVotesPanel } from '../components/ItemVotesPanel';
import { ReportButton } from '../components/ReportButton';
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
import { Button } from '../components/ui/button';
import { isResultsLinkState, type ResultsLinkState, resultsPath } from '../constants/routes';
import { translateError } from '../errors/apiError';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { PageContainer } from '../components/PageContainer';

export function ResultsPage() {
  const { token = '' }: Readonly<Params> = useParams();
  return <GameResults key={token} token={token} />;
}

function GameResults({ token }: { token: string }) {
  const location: Location = useLocation();
  const [includeAbsentVotes, setIncludeAbsentVotes] = useState<boolean>(true);
  const [view, setView] = useState<ResultsView>('median');
  const [chosenItemId, setChosenItemId] = useState<string | null>(null);
  const [revealedViews, setRevealedViews] = useState<ReadonlySet<ResultsView>>(new Set());
  const [revealRun, setRevealRun] = useState<number>(0);
  const markRevealed = useCallback(() => {
    setRevealedViews((revealed: ReadonlySet<ResultsView>) =>
      revealed.has(view) ? revealed : new Set(revealed).add(view),
    );
  }, [view]);
  const state: GameResultsState = useGameResults(token, includeAbsentVotes);
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const fromRoom: ResultsLinkState | null = isResultsLinkState(location.state)
    ? location.state
    : null;

  if (state.anyVariant === undefined) {
    return (
      <PageContainer width="app" className="flex flex-col items-start gap-6">
        {state.error === null ? (
          <LoadingSkeleton shape="board" />
        ) : (
          <ErrorMessage>{translateError(t, state.error)}</ErrorMessage>
        )}
      </PageContainer>
    );
  }

  const known: GameResults = state.anyVariant;
  const items: ResultItems = new Map(
    known.items.map((item: GameItem, index: number): [string, ResultItem] => {
      const imageLabel: string = t('results.itemImage', { number: index + 1 });
      return [item.id, { item, imageLabel, name: item.text ?? imageLabel }];
    }),
  );

  const panelHasFocusableItems: boolean =
    state.results !== undefined &&
    known.items.length > 0 &&
    !(view === 'players' && state.results.players.length === 0);

  const revealable: boolean = view !== 'overall' && state.results !== undefined;

  function replayReveal() {
    setRevealedViews((revealed: ReadonlySet<ResultsView>) => {
      const next: Set<ResultsView> = new Set(revealed);
      next.delete(view);
      return next;
    });
    setRevealRun((run: number) => run + 1);
  }

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
    <PageContainer width="app" className="flex flex-col items-start gap-6">
      {fromRoom !== null && <ResultsRoomActions fromRoom={fromRoom} />}
      <div className="flex w-full flex-wrap items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold">
            {t('results.title', { name: known.template_name })}
          </h1>
          <p className="text-muted-foreground">
            {t('results.closedAt', { date: new Date(known.closed_at) })}
          </p>
        </div>
        <ReportButton
          targetKind="game"
          targetId={known.game_id}
          contentName={known.template_name}
        />
      </div>
      <CopyLinkField
        label={t('results.publicLink')}
        link={`${window.location.origin}${resultsPath(token)}`}
      />
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
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
        {revealable && (
          <Button type="button" variant="outline" size="sm" onClick={replayReveal}>
            {t('results.replayReveal')}
          </Button>
        )}
      </div>
      <div className="grid w-full items-start gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="flex min-w-0 flex-col gap-4">
          <ResultsTabs selected={view} onSelect={setView} />
          <div
            role="tabpanel"
            id={resultsPanelId(view)}
            aria-labelledby={resultsTabId(view)}
            aria-busy={state.isPending}
            tabIndex={panelHasFocusableItems ? undefined : 0}
            className="w-full rounded-xl outline-none focus-visible:ring-3 focus-visible:ring-ring"
          >
            {state.results !== undefined ? (
              <ResultsViewContent
                view={view}
                results={state.results}
                items={items}
                selection={selection}
                reveal={!revealedViews.has(view)}
                revealRun={revealRun}
                onRevealStarted={markRevealed}
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
    </PageContainer>
  );
}

interface ResultsViewContentProps {
  view: ResultsView;
  results: GameResults;
  items: ResultItems;
  selection: ItemSelection;
  reveal: boolean;
  revealRun: number;
  onRevealStarted: () => void;
}

function ResultsViewContent({
  view,
  results,
  items,
  selection,
  reveal,
  revealRun,
  onRevealStarted,
}: ResultsViewContentProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();

  if (view === 'median') {
    return (
      <ResultsTierList
        key={revealRun}
        tiers={results.tiers}
        rows={results.median_ranking}
        items={items}
        extraRow={{ label: t('results.median.unranked'), itemIds: results.unranked_item_ids }}
        selection={selection}
        revealOnMount={reveal}
        onRevealStarted={onRevealStarted}
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
      reveal={reveal}
      revealRun={revealRun}
      onRevealStarted={onRevealStarted}
    />
  );
}
