import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { ItemDistribution } from '../api/results';
import type { GameTier } from '../api/rooms';
import { tierColorStyle } from './boardStyles';
import { GameItemView } from './GameItemView';
import { ResultItemButton } from './ResultItemButton';
import type { ItemSelection, ResultItem, ResultItems } from './resultsViews';

interface ResultsDistributionTableProps {
  tiers: GameTier[];
  items: ResultItems;
  distribution: ItemDistribution[];
  includeAbsentVotes: boolean;
  selection: ItemSelection;
}

// Vue globale (US-5.2) : pour chaque item, combien de joueurs l'ont mis dans chaque tier, et
// combien étaient absents. Le tableau défile seul sur un petit écran, pas la page
export function ResultsDistributionTable({
  tiers,
  items,
  distribution,
  includeAbsentVotes,
  selection,
}: ResultsDistributionTableProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();

  return (
    <div className="w-full overflow-x-auto rounded-panel border bg-card">
      <table className="w-full text-sm">
        <caption className="sr-only">{t('results.overall.caption')}</caption>
        <thead>
          <tr className="border-b bg-muted/50">
            <th scope="col" className="px-3 py-2 text-left font-medium">
              {t('results.overall.item')}
            </th>
            {tiers.map((tier: GameTier) => (
              <th key={tier.id} scope="col" className="px-3 py-2 text-center">
                <span
                  style={tierColorStyle(tier.color)}
                  className="inline-flex min-w-8 justify-center rounded-md px-1.5 py-0.5 font-heading font-black"
                >
                  {tier.name}
                </span>
              </th>
            ))}
            {includeAbsentVotes && (
              <th scope="col" className="px-3 py-2 text-center font-medium">
                {t('results.overall.absent')}
              </th>
            )}
          </tr>
        </thead>
        <tbody>
          {distribution.map((entry: ItemDistribution) => {
            const resultItem: ResultItem | undefined = items.get(entry.item_id);
            if (resultItem === undefined) return null;
            return (
              <tr key={entry.item_id} className="border-b last:border-0">
                <th scope="row" className="px-3 py-2 text-left font-normal">
                  <ResultItemButton
                    itemId={entry.item_id}
                    name={resultItem.item.text ?? resultItem.imageLabel}
                    selection={selection}
                    className="rounded-md p-1"
                  >
                    <GameItemView
                      item={resultItem.item}
                      imageLabel={resultItem.imageLabel}
                      size="small"
                    />
                  </ResultItemButton>
                </th>
                {entry.votes_per_tier.map((votes: number, index: number) => (
                  <td
                    key={tiers[index]?.id ?? index}
                    className={
                      votes === 0
                        ? 'px-3 py-2 text-center text-muted-foreground'
                        : 'px-3 py-2 text-center font-semibold'
                    }
                  >
                    {votes}
                  </td>
                ))}
                {includeAbsentVotes && (
                  <td className="px-3 py-2 text-center text-muted-foreground">
                    {entry.absent_count}
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
