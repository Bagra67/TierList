import { cn } from 'cn';
import { type AnimationEvent, type CSSProperties, useEffect, useId, useState } from 'react';
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
  // Les lignes apparaissent une à une, du bas vers le haut (sauf mouvement réduit). Lu au montage
  // seulement : pour rejouer la révélation, la tier list est montée à nouveau (key)
  reveal?: boolean;
  // Appelé quand la révélation commence : la vue compte alors comme révélée
  onRevealStarted?: () => void;
}

// Classe et délai d'animation d'une ligne pendant la révélation
type RevealProps = { className?: string; style?: CSSProperties };

// Une tier list en lecture seule : le classement médian, ou le classement final d'un joueur.
// Chaque ligne est un groupe nommé par son tier, que le lecteur d'écran annonce avec ses items
export function ResultsTierList({
  tiers,
  rows,
  items,
  extraRow,
  selection,
  reveal = false,
  onRevealStarted,
}: ResultsTierListProps) {
  const idPrefix: string = useId();
  const itemIdsByTier: ReadonlyMap<string, string[]> = new Map(
    rows.map((row: TierItems) => [row.tier_id, row.item_ids]),
  );
  const visibleExtraRow: { label: string; itemIds: string[] } | undefined =
    extraRow !== undefined && extraRow.itemIds.length > 0 ? extraRow : undefined;
  const rowCount: number = tiers.length + (visibleExtraRow === undefined ? 0 : 1);
  // Figé au montage, puis éteint quand la ligne du haut a fini d'apparaître : une ligne ajoutée
  // ensuite (autre joueur, autre variante) n'est pas animée seule. En mouvement réduit, rien ne
  // s'anime (motion-safe) et la fin n'arrive jamais, sans effet
  const [revealing, setRevealing] = useState<boolean>(reveal);

  useEffect(() => {
    if (revealing) onRevealStarted?.();
  }, [revealing, onRevealStarted]);

  // Ligne d'indice index (0 = en haut) : la dernière apparaît la première, le tier du haut en
  // dernier, pour garder le suspense
  function revealProps(index: number): RevealProps {
    if (!revealing) return {};
    return {
      className: 'motion-safe:animate-reveal',
      style: { animationDelay: `${(rowCount - 1 - index) * REVEAL_STEP_MS}ms` },
    };
  }
  const extraAnimation: RevealProps = revealProps(tiers.length);

  function handleTopRowAnimationEnd(event: AnimationEvent<HTMLDivElement>) {
    if (event.target === event.currentTarget) setRevealing(false);
  }

  return (
    <div className={panelVariants({ variant: 'list' })}>
      {tiers.map((tier: GameTier, index: number) => {
        const labelId: string = `${idPrefix}-tier-${index}`;
        const animation: RevealProps = revealProps(index);
        return (
          <div
            key={tier.id}
            role="group"
            aria-labelledby={labelId}
            className={cn('flex items-center gap-3 pr-3', animation.className)}
            style={animation.style}
            onAnimationEnd={index === 0 ? handleTopRowAnimationEnd : undefined}
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
      {visibleExtraRow !== undefined && (
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
            {visibleExtraRow.label}
          </span>
          <ItemList itemIds={visibleExtraRow.itemIds} items={items} selection={selection} />
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
