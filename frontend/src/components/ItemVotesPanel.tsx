import { cn } from 'cn';
import { type CSSProperties, type ReactNode, useId } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { ItemDistribution } from '../api/results';
import type { GameTier } from '../api/rooms';
import { ITEM_CHIP_CLASS, tierColorStyle } from './boardStyles';
import { GameItemView } from './GameItemView';
import { ReportButton } from './ReportButton';
import type { ResultItem } from './resultsViews';
import { panelVariants } from './ui/panel';

const ABSENT_BAR_STYLE: CSSProperties = {
  backgroundImage: 'repeating-linear-gradient(135deg, currentColor 0 3px, transparent 3px 7px)',
};

interface ItemVotesPanelProps {
  tiers: GameTier[];
  resultItem: ResultItem;
  distribution: ItemDistribution;
  playerNames: string[];
  includeAbsentVotes: boolean;
}

export function ItemVotesPanel({
  tiers,
  resultItem,
  distribution,
  playerNames,
  includeAbsentVotes,
}: ItemVotesPanelProps) {
  const { t, i18n }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const headingId: string = useId();
  const playerCount: number = Math.max(playerNames.length, 1);
  const nameList: Intl.ListFormat = new Intl.ListFormat(i18n.language, {
    style: 'long',
    type: 'conjunction',
  });

  function namesOf(indexes: number[] | undefined): string | undefined {
    if (indexes === undefined || indexes.length === 0) return undefined;
    return nameList.format(indexes.map((index: number) => playerNames[index] ?? ''));
  }

  return (
    <section aria-labelledby={headingId} className={panelVariants()}>
      <div className="flex items-center gap-3">
        <span className={ITEM_CHIP_CLASS}>
          <GameItemView item={resultItem.item} imageLabel={resultItem.imageLabel} size="small" />
        </span>
        <h2 id={headingId} aria-live="polite" className="font-semibold">
          {t('results.votes.title', { item: resultItem.name })}
        </h2>
      </div>
      {resultItem.item.image_url !== null && (
        <div>
          <ReportButton
            key={resultItem.item.id}
            targetKind="item"
            targetId={resultItem.item.id}
            contentName={resultItem.imageLabel}
          />
        </div>
      )}
      <ul className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-x-2 gap-y-3">
        {tiers.map((tier: GameTier, index: number) => (
          <VoteLine
            key={tier.id}
            label={
              <span
                title={tier.name}
                style={tierColorStyle(tier.color)}
                className="inline-block max-w-24 min-w-8 truncate rounded-md px-1.5 text-center font-heading font-black"
              >
                {tier.name}
              </span>
            }
            count={distribution.votes_per_tier[index] ?? 0}
            playerCount={playerCount}
            names={namesOf(distribution.player_indexes_per_tier?.[index])}
            barStyle={{ backgroundColor: tier.color }}
          />
        ))}
        {includeAbsentVotes && (
          <VoteLine
            label={<span className="text-sm font-semibold">{t('results.votes.absent')}</span>}
            count={distribution.absent_count}
            playerCount={playerCount}
            names={namesOf(distribution.absent_player_indexes ?? undefined)}
            barStyle={ABSENT_BAR_STYLE}
            barClassName="border border-muted-foreground text-muted-foreground"
          />
        )}
      </ul>
    </section>
  );
}

interface VoteLineProps {
  label: ReactNode;
  count: number;
  playerCount: number;
  names: string | undefined;
  barStyle: CSSProperties;
  barClassName?: string;
}

function VoteLine({ label, count, playerCount, names, barStyle, barClassName }: VoteLineProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  return (
    <li className="col-span-3 grid grid-cols-subgrid items-center gap-y-1">
      {label}
      <span className="h-3.5 w-full" aria-hidden="true">
        {count > 0 && (
          <span
            className={cn('block h-full min-w-1 rounded-sm', barClassName)}
            style={{ ...barStyle, width: `${(count / playerCount) * 100}%` }}
          />
        )}
      </span>
      <span className="text-sm tabular-nums">{t('results.votes.count', { count })}</span>
      {names !== undefined && (
        <p className="col-span-2 col-start-2 text-sm text-muted-foreground">{names}</p>
      )}
    </li>
  );
}
