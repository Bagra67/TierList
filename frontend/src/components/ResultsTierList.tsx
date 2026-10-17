import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { TierItems } from '../api/results';
import type { GameItem, GameTier } from '../api/rooms';
import { TierLabel } from './gameBoardParts';
import { GameItemView } from './GameItemView';

interface ResultsTierListProps {
  tiers: GameTier[];
  // Un élément par tier, de haut en bas
  rows: TierItems[];
  itemsById: ReadonlyMap<string, GameItem>;
  // Ligne ajoutée sous les tiers (non classés, jamais placés), absente si elle est vide
  extraRow?: { label: string; itemIds: string[] };
}

// Une tier list en lecture seule : le classement médian, ou le classement final d'un joueur
export function ResultsTierList({ tiers, rows, itemsById, extraRow }: ResultsTierListProps) {
  const itemIdsByTier: ReadonlyMap<string, string[]> = new Map(
    rows.map((row: TierItems) => [row.tier_id, row.item_ids]),
  );

  return (
    <div className="flex w-full flex-col divide-y rounded-xl border">
      {tiers.map((tier: GameTier) => (
        <div key={tier.id} className="flex items-center gap-3 px-3 py-2">
          <TierLabel tier={tier} />
          <ItemList itemIds={itemIdsByTier.get(tier.id) ?? []} itemsById={itemsById} />
        </div>
      ))}
      {extraRow !== undefined && extraRow.itemIds.length > 0 && (
        <div className="flex items-center gap-3 px-3 py-2">
          <span className="min-w-16 text-sm font-semibold text-muted-foreground">
            {extraRow.label}
          </span>
          <ItemList itemIds={extraRow.itemIds} itemsById={itemsById} />
        </div>
      )}
    </div>
  );
}

function ItemList({
  itemIds,
  itemsById,
}: {
  itemIds: string[];
  itemsById: ReadonlyMap<string, GameItem>;
}) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  if (itemIds.length === 0) {
    return <span className="text-sm text-muted-foreground">{t('results.emptyTier')}</span>;
  }
  return (
    <ul className="flex flex-wrap gap-2">
      {itemIds.map((itemId: string) => {
        const item: GameItem | undefined = itemsById.get(itemId);
        if (item === undefined) return null;
        return (
          <li key={itemId} className="rounded-md border bg-card px-2 py-1">
            <GameItemView item={item} imageLabel={t('results.itemImage')} size="small" />
          </li>
        );
      })}
    </ul>
  );
}
