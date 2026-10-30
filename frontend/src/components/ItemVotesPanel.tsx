import { cn } from 'cn';
import { type CSSProperties, type ReactNode, useId } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { ItemDistribution } from '../api/results';
import type { GameTier } from '../api/rooms';
import { ITEM_CHIP_CLASS, tierColorStyle } from './boardStyles';
import { GameItemView } from './GameItemView';
import type { ResultItem } from './resultsViews';
import { panelVariants } from './ui/panel';

// Hachures de la barre des absents : ils n'ont pas de tier, donc pas de couleur
const ABSENT_BAR_STYLE: CSSProperties = {
  backgroundImage: 'repeating-linear-gradient(135deg, currentColor 0 3px, transparent 3px 7px)',
};

interface ItemVotesPanelProps {
  tiers: GameTier[];
  resultItem: ResultItem;
  distribution: ItemDistribution;
  // Noms des joueurs, dans l'ordre de la réponse (les indices de distribution y renvoient)
  playerNames: string[];
  includeAbsentVotes: boolean;
}

// Détail d'un item : pour chaque tier, combien de joueurs l'y ont mis et lesquels, puis les absents.
// Le même décompte que la vue globale, avec les noms (le serveur dit qui est compté, case comprise)
export function ItemVotesPanel({
  tiers,
  resultItem,
  distribution,
  playerNames,
  includeAbsentVotes,
}: ItemVotesPanelProps) {
  const { t, i18n }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const headingId: string = useId();
  const itemName: string = resultItem.item.text ?? resultItem.imageLabel;
  // Une barre pleine = tous les joueurs
  const playerCount: number = Math.max(playerNames.length, 1);
  const nameList: Intl.ListFormat = new Intl.ListFormat(i18n.language, {
    style: 'long',
    type: 'conjunction',
  });

  function namesOf(indexes: number[]): string {
    return nameList.format(indexes.map((index: number) => playerNames[index] ?? ''));
  }

  return (
    <section aria-labelledby={headingId} className={panelVariants()}>
      <div className="flex items-center gap-3">
        <span className={ITEM_CHIP_CLASS}>
          <GameItemView item={resultItem.item} imageLabel={resultItem.imageLabel} size="small" />
        </span>
        {/* Annoncé quand un autre item est choisi */}
        <h2 id={headingId} aria-live="polite" className="font-semibold">
          {t('results.votes.title', { item: itemName })}
        </h2>
      </div>
      <ul className="flex flex-col gap-3">
        {tiers.map((tier: GameTier, index: number) => {
          const voters: number[] = distribution.player_indexes_per_tier[index] ?? [];
          return (
            <li key={tier.id} className="flex flex-col gap-1">
              <VoteBar
                label={
                  <span
                    style={tierColorStyle(tier.color)}
                    className="inline-flex min-w-8 justify-center rounded-md px-1.5 font-heading font-black"
                  >
                    {tier.name}
                  </span>
                }
                count={voters.length}
                ratio={voters.length / playerCount}
                barStyle={{ backgroundColor: tier.color }}
              />
              {voters.length > 0 && (
                <p className="pl-11 text-sm text-muted-foreground">{namesOf(voters)}</p>
              )}
            </li>
          );
        })}
        {includeAbsentVotes && (
          <li className="flex flex-col gap-1">
            <VoteBar
              label={<span className="text-sm font-semibold">{t('results.votes.absent')}</span>}
              count={distribution.absent_player_indexes.length}
              ratio={distribution.absent_player_indexes.length / playerCount}
              barStyle={ABSENT_BAR_STYLE}
              barClassName="border border-muted-foreground text-muted-foreground"
            />
            {distribution.absent_player_indexes.length > 0 && (
              <p className="pl-11 text-sm text-muted-foreground">
                {namesOf(distribution.absent_player_indexes)}
              </p>
            )}
          </li>
        )}
      </ul>
    </section>
  );
}

interface VoteBarProps {
  label: ReactNode;
  count: number;
  // Part des joueurs, de 0 à 1
  ratio: number;
  barStyle: CSSProperties;
  barClassName?: string;
}

// Une ligne : le tier, une barre proportionnelle au nombre de votes, et ce nombre en texte (la
// barre seule ne suffirait pas)
function VoteBar({ label, count, ratio, barStyle, barClassName }: VoteBarProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  return (
    <div className="grid grid-cols-[2.25rem_minmax(0,1fr)_auto] items-center gap-2">
      {label}
      <span className="h-3.5 w-full" aria-hidden="true">
        {count > 0 && (
          <span
            className={cn('block h-full min-w-1 rounded-sm', barClassName)}
            style={{ ...barStyle, width: `${ratio * 100}%` }}
          />
        )}
      </span>
      <span className="text-sm tabular-nums">{t('results.votes.count', { count })}</span>
    </div>
  );
}
