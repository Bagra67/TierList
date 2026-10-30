import { cn } from 'cn';
import { type CSSProperties, useId } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { TierItems } from '../api/results';
import type { GameTier } from '../api/rooms';
import { REVEAL_STEP_MS } from '../constants/results';
import { ITEM_CHIP_CLASS, TIER_LABEL_CLASS } from './boardStyles';
import { TierLabel } from './gameBoardParts';
import { GameItemView } from './GameItemView';
import { ResultItemButton } from './ResultItemButton';
import type { ItemSelection, ResultItem, ResultItems } from './resultsViews';
import { panelVariants } from './ui/panel';

interface ResultsTierListProps {
  tiers: GameTier[];
  // Un élément par tier, de haut en bas
  rows: TierItems[];
  items: ResultItems;
  // Ligne ajoutée sous les tiers (non classés, jamais placés), absente si elle est vide
  extraRow?: { label: string; itemIds: string[] };
  // Cliquer un item ouvre ses votes
  selection: ItemSelection;
  // Les lignes apparaissent une à une, du bas vers le haut (sauf mouvement réduit)
  reveal?: boolean;
}

// Une tier list en lecture seule : le classement médian, ou le classement final d'un joueur.
// Chaque ligne est un groupe nommé par son tier, que le lecteur d'écran annonce avec ses items
export function ResultsTierList({
  tiers,
  rows,
  items,
  extraRow,
  selection,
  reveal = false,
}: ResultsTierListProps) {
  const idPrefix: string = useId();
  const itemIdsByTier: ReadonlyMap<string, string[]> = new Map(
    rows.map((row: TierItems) => [row.tier_id, row.item_ids]),
  );
  const showsExtraRow: boolean = extraRow !== undefined && extraRow.itemIds.length > 0;
  const rowCount: number = tiers.length + (showsExtraRow ? 1 : 0);

  // Ligne d'indice index (0 = en haut) : la dernière apparaît la première, le tier du haut en
  // dernier, pour garder le suspense
  function revealProps(index: number): { className?: string; style?: CSSProperties } {
    if (!reveal) return {};
    return {
      className: 'motion-safe:animate-reveal',
      style: { animationDelay: `${(rowCount - 1 - index) * REVEAL_STEP_MS}ms` },
    };
  }
  const extraAnimation: { className?: string; style?: CSSProperties } = revealProps(tiers.length);

  return (
    <div className={panelVariants({ variant: 'list' })}>
      {tiers.map((tier: GameTier, index: number) => {
        const labelId: string = `${idPrefix}-tier-${index}`;
        const animation: { className?: string; style?: CSSProperties } = revealProps(index);
        return (
          <div
            key={tier.id}
            role="group"
            aria-labelledby={labelId}
            className={cn('flex items-center gap-3 pr-3', animation.className)}
            style={animation.style}
          >
            <TierLabel tier={tier} id={labelId} />
            <ItemList
              itemIds={itemIdsByTier.get(tier.id) ?? []}
              items={items}
              selection={selection}
            />
          </div>
        );
      })}
      {showsExtraRow && extraRow !== undefined && (
        <div
          role="group"
          aria-labelledby={`${idPrefix}-extra`}
          className={cn('flex items-center gap-3 pr-3', extraAnimation.className)}
          style={extraAnimation.style}
        >
          <span
            id={`${idPrefix}-extra`}
            className={cn(TIER_LABEL_CLASS, 'bg-muted text-sm font-semibold text-muted-foreground')}
          >
            {extraRow.label}
          </span>
          <ItemList itemIds={extraRow.itemIds} items={items} selection={selection} />
        </div>
      )}
    </div>
  );
}

interface ItemListProps {
  itemIds: string[];
  items: ResultItems;
  selection: ItemSelection;
}

function ItemList({ itemIds, items, selection }: ItemListProps) {
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
          <li key={itemId}>
            <ResultItemButton
              resultItem={resultItem}
              selection={selection}
              labelled
              className={cn(ITEM_CHIP_CLASS, 'hover:border-primary')}
            >
              <GameItemView
                item={resultItem.item}
                imageLabel={resultItem.imageLabel}
                size="small"
              />
            </ResultItemButton>
          </li>
        );
      })}
    </ul>
  );
}
