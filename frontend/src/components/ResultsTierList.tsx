import { useId } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { TierItems } from '../api/results';
import type { GameTier } from '../api/rooms';
import { ITEM_CHIP_CLASS } from './boardStyles';
import { TierLabel } from './gameBoardParts';
import { GameItemView } from './GameItemView';
import type { ResultItem, ResultItems } from './resultsViews';

interface ResultsTierListProps {
  tiers: GameTier[];
  // Un élément par tier, de haut en bas
  rows: TierItems[];
  items: ResultItems;
  // Ligne ajoutée sous les tiers (non classés, jamais placés), absente si elle est vide
  extraRow?: { label: string; itemIds: string[] };
}

// Une tier list en lecture seule : le classement médian, ou le classement final d'un joueur.
// Chaque ligne est un groupe nommé par son tier, que le lecteur d'écran annonce avec ses items
export function ResultsTierList({ tiers, rows, items, extraRow }: ResultsTierListProps) {
  const idPrefix: string = useId();
  const itemIdsByTier: ReadonlyMap<string, string[]> = new Map(
    rows.map((row: TierItems) => [row.tier_id, row.item_ids]),
  );

  return (
    <div className="flex w-full flex-col divide-y overflow-hidden rounded-xl border bg-card">
      {tiers.map((tier: GameTier, index: number) => {
        const labelId: string = `${idPrefix}-tier-${index}`;
        return (
          <div
            key={tier.id}
            role="group"
            aria-labelledby={labelId}
            className="flex items-center gap-3 pr-3"
          >
            <TierLabel tier={tier} id={labelId} />
            <ItemList itemIds={itemIdsByTier.get(tier.id) ?? []} items={items} />
          </div>
        );
      })}
      {extraRow !== undefined && extraRow.itemIds.length > 0 && (
        <div
          role="group"
          aria-labelledby={`${idPrefix}-extra`}
          className="flex items-center gap-3 pr-3"
        >
          <span
            id={`${idPrefix}-extra`}
            className="flex min-h-14 w-16 shrink-0 items-center justify-center self-stretch bg-muted px-1 text-center text-sm font-semibold text-muted-foreground sm:min-h-16 sm:w-20"
          >
            {extraRow.label}
          </span>
          <ItemList itemIds={extraRow.itemIds} items={items} />
        </div>
      )}
    </div>
  );
}

function ItemList({ itemIds, items }: { itemIds: string[]; items: ResultItems }) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  if (itemIds.length === 0) {
    return <span className="py-2 text-sm text-muted-foreground">{t('results.emptyTier')}</span>;
  }
  return (
    <ul className="flex flex-wrap gap-2 py-2">
      {itemIds.map((itemId: string) => {
        const resultItem: ResultItem | undefined = items.get(itemId);
        if (resultItem === undefined) return null;
        return (
          <li key={itemId} className={ITEM_CHIP_CLASS}>
            <GameItemView item={resultItem.item} imageLabel={resultItem.imageLabel} size="small" />
          </li>
        );
      })}
    </ul>
  );
}
