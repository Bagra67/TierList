import {
  closestCenter,
  DndContext,
  useDroppable,
  type Announcements,
  type DragEndEvent,
  type DragStartEvent,
} from '@dnd-kit/core';
import { cn } from 'cn';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import { type ReactNode, useRef, useState } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import {
  type CurrentGame,
  type GameItem,
  type GameTier,
  type OwnPlacement,
  type Room,
  usePlaceItem,
} from '../api/rooms';
import { translateError } from '../errors/apiError';
import { type BoardDropTarget, type DropSide, dropPosition, dropSide } from './boardPositions';
import { ErrorMessage } from './ErrorMessage';
import { useBoardSensors, useFocusAfterUpdate } from './boardHooks';
import { ITEM_CHIP_CLASS } from './boardStyles';
import { DragPreview, DraggableItem, EndSlot, TierLabel } from './gameBoardParts';
import { GameItemView } from './GameItemView';
import { Button } from './ui/button';
import { panelVariants } from './ui/panel';

// Clés de focus de l'item en cours (useFocusAfterUpdate)
const CURRENT_FOCUS = { drag: 'current:drag', earlier: 'current:earlier', later: 'current:later' };

interface GameBoardProps {
  room: Room;
  game: CurrentGame;
}

// Le plateau privé du lecteur (US-3.3) : ses tiers, les items qu'il a déjà placés (ils ne bougent
// plus avant le cooldown) et l'item en cours, à déposer dans un tier à la position voulue. À la
// souris ou au doigt par glisser-déposer ; au clavier par les boutons « Placer dans » et ←/→.
export function GameBoard({ room, game }: GameBoardProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const placeMutation = usePlaceItem(room.code);
  const sensors = useBoardSensors();
  const sectionRef = useRef<HTMLElement>(null);
  const focus = useFocusAfterUpdate(sectionRef, game.own_placements);
  const currentItem: GameItem = game.current_item;
  // L'id du glisser porte l'item : un glisser commencé avant la fin du tour ne pose pas le suivant
  const draggableId: string = `current:${currentItem.id}`;
  const currentPlacement: OwnPlacement | undefined = game.own_placements.find(
    (placement) => placement.item.id === currentItem.id,
  );
  const itemLabel: string = currentItem.text ?? t('rooms.game.currentItemImage');
  const pending: boolean = placeMutation.isPending;
  // Identifiant de l'item glissé, pour son aperçu (DragPreview)
  const [draggedId, setDraggedId] = useState<string | null>(null);

  // Les items d'un tier, l'item en cours compris s'il y est, dans l'ordre (le serveur les trie)
  function idsIn(tierId: string): string[] {
    return game.own_placements
      .filter((placement) => placement.tier_id === tierId)
      .map((placement) => placement.item.id);
  }

  function othersIn(tierId: string): OwnPlacement[] {
    return game.own_placements.filter(
      (placement) => placement.tier_id === tierId && placement.item.id !== currentItem.id,
    );
  }

  function tierName(tierId: string): string {
    return game.tiers.find((tier) => tier.id === tierId)?.name ?? '';
  }

  async function placeAt(tierId: string, position: number, focusKeys: string[]) {
    if (pending) return;
    focus.request(focusKeys);
    try {
      await placeMutation.mutateAsync({ tileId: currentItem.id, tierId, position });
    } catch {
      focus.cancel();
      return; // l'erreur est affichée depuis placeMutation.error
    }
  }

  function positionFor(target: BoardDropTarget, side: DropSide): number | null {
    return dropPosition(idsIn(target.tierId), currentItem.id, target, side);
  }

  function describe(target: BoardDropTarget, side: DropSide): string {
    const position: number | null = positionFor(target, side);
    if (position === null) return t('rooms.game.dnd.unchanged', { item: itemLabel });
    return t('rooms.game.dnd.over', {
      item: itemLabel,
      tier: tierName(target.tierId),
      position: position + 1,
    });
  }

  const announcements: Announcements = {
    onDragStart: () => t('rooms.game.dnd.pickedUp', { item: itemLabel }),
    onDragOver: ({ active, over }) =>
      over?.data.current === undefined
        ? undefined
        : describe(
            over.data.current as BoardDropTarget,
            dropSide(active.rect.current.translated, over.rect),
          ),
    onDragEnd: ({ active, over }) => {
      if (over?.data.current === undefined) return undefined;
      const target: BoardDropTarget = over.data.current as BoardDropTarget;
      const position: number | null = positionFor(
        target,
        dropSide(active.rect.current.translated, over.rect),
      );
      if (position === null) return t('rooms.game.dnd.unchanged', { item: itemLabel });
      return t('rooms.game.dnd.dropped', {
        item: itemLabel,
        tier: tierName(target.tierId),
        position: position + 1,
      });
    },
    onDragCancel: () => t('rooms.game.dnd.cancelled', { item: itemLabel }),
  };

  function handleDragStart({ active }: DragStartEvent) {
    setDraggedId(String(active.id));
  }

  function handleDragEnd({ active, over }: DragEndEvent) {
    setDraggedId(null);
    if (active.id !== draggableId || over?.data.current === undefined) return;
    const target: BoardDropTarget = over.data.current as BoardDropTarget;
    const position: number | null = positionFor(
      target,
      dropSide(active.rect.current.translated, over.rect),
    );
    if (position === null) return;
    void placeAt(target.tierId, position, [CURRENT_FOCUS.drag]);
  }

  return (
    <section ref={sectionRef} className="flex w-full flex-col gap-3">
      <h2 className="text-lg font-semibold">{t('rooms.game.board')}</h2>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
        onDragCancel={() => setDraggedId(null)}
        accessibility={{
          announcements,
          screenReaderInstructions: { draggable: t('rooms.game.dnd.instructions') },
        }}
      >
        {currentPlacement === undefined && (
          <div className={cn(panelVariants({ variant: 'dashed' }), 'items-start')}>
            <p className="text-sm text-muted-foreground">{t('rooms.game.dock')}</p>
            {/* L'item est affiché en grand au-dessus : ici, seulement la poignée à glisser */}
            <DraggableItem
              id={draggableId}
              label={itemLabel}
              ariaLabel={t('rooms.game.dragHandleLabel', { item: itemLabel })}
              focusKey={CURRENT_FOCUS.drag}
              disabled={pending}
              emphasized
            >
              <span className="px-2 font-medium">{t('rooms.game.dragHandle')}</span>
            </DraggableItem>
          </div>
        )}
        <ol className="flex w-full flex-col gap-2">
          {game.tiers.map((tier) => (
            <TierRow
              key={tier.id}
              tier={tier}
              others={othersIn(tier.id)}
              currentPlacement={
                currentPlacement?.tier_id === tier.id ? currentPlacement : undefined
              }
              currentItem={currentItem}
              draggableId={draggableId}
              itemLabel={itemLabel}
              pending={pending}
              onPlace={(position, focusKeys) => void placeAt(tier.id, position, focusKeys)}
            />
          ))}
        </ol>
        <DragPreview>
          {draggedId === draggableId ? (
            <GameItemView item={currentItem} imageLabel={itemLabel} size="small" />
          ) : null}
        </DragPreview>
      </DndContext>
      {placeMutation.isError && (
        <ErrorMessage>{translateError(t, placeMutation.error)}</ErrorMessage>
      )}
    </section>
  );
}

interface TierRowProps {
  tier: GameTier;
  others: OwnPlacement[];
  // L'item en cours, s'il est déjà placé dans ce tier
  currentPlacement: OwnPlacement | undefined;
  currentItem: GameItem;
  draggableId: string;
  itemLabel: string;
  pending: boolean;
  // Place l'item en cours à ce rang du tier, puis rend le focus au premier de ces contrôles
  onPlace: (position: number, focusKeys: string[]) => void;
}

function TierRow({
  tier,
  others,
  currentPlacement,
  currentItem,
  draggableId,
  itemLabel,
  pending,
  onPlace,
}: TierRowProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  // Rang de l'item en cours parmi les autres items du tier : il est affiché avant others[rank]
  const currentRank: number | undefined = currentPlacement?.position;
  const placeFocus: string = `place:${tier.id}`;

  const currentChip = (
    <li className="flex items-center gap-1">
      <DraggableItem
        id={draggableId}
        label={itemLabel}
        focusKey={CURRENT_FOCUS.drag}
        disabled={pending}
        emphasized
      >
        <GameItemView item={currentItem} imageLabel={itemLabel} size="small" />
      </DraggableItem>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        data-focus-key={CURRENT_FOCUS.earlier}
        aria-label={t('rooms.game.moveEarlier', { item: itemLabel })}
        aria-disabled={pending}
        disabled={currentRank === undefined || currentRank === 0}
        onClick={() =>
          onPlace((currentRank ?? 0) - 1, [CURRENT_FOCUS.earlier, CURRENT_FOCUS.later])
        }
      >
        <ArrowLeft />
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        data-focus-key={CURRENT_FOCUS.later}
        aria-label={t('rooms.game.moveLater', { item: itemLabel })}
        aria-disabled={pending}
        disabled={currentRank === undefined || currentRank >= others.length}
        onClick={() =>
          onPlace((currentRank ?? 0) + 1, [CURRENT_FOCUS.later, CURRENT_FOCUS.earlier])
        }
      >
        <ArrowRight />
      </Button>
    </li>
  );

  return (
    <li className="flex w-full rounded-[10px] border bg-card">
      {/* Coin arrondi du bloc-lettre : le rayon de la ligne moins sa bordure. Pas d'overflow-hidden
          sur la ligne, qui rognerait l'item glissé vers un autre tier */}
      <TierLabel tier={tier} className="rounded-l-[9px]" />
      <div className="flex flex-1 flex-wrap items-center gap-2 p-2">
        <ol className="flex flex-1 flex-wrap items-center gap-2" aria-label={tier.name}>
          {others.map((placement, index) => (
            <PlacedItemSlot
              key={placement.item.id}
              placement={placement}
              target={{ tierId: tier.id, itemId: placement.item.id }}
              before={currentRank === index ? currentChip : null}
            />
          ))}
          {currentRank !== undefined && currentRank >= others.length && currentChip}
          <EndSlot id={`${tier.id}:end`} data={{ tierId: tier.id, itemId: null }} />
        </ol>
        <Button
          type="button"
          variant="outline"
          size="sm"
          data-focus-key={placeFocus}
          aria-label={t('rooms.game.placeInLabel', { tier: tier.name })}
          aria-disabled={pending}
          onClick={() => onPlace(others.length, [placeFocus])}
        >
          {t('rooms.game.placeIn', { tier: tier.name })}
        </Button>
      </div>
    </li>
  );
}

interface PlacedItemSlotProps {
  placement: OwnPlacement;
  target: BoardDropTarget;
  // L'item en cours, affiché juste avant cet item
  before: ReactNode;
}

// Un item d'un tour passé : il ne bouge pas, mais déposer l'item en cours dessus le place avant
// ou après lui, selon le côté où il tombe
function PlacedItemSlot({ placement, target, before }: PlacedItemSlotProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const { setNodeRef, isOver }: ReturnType<typeof useDroppable> = useDroppable({
    id: `${target.tierId}:${placement.item.id}`,
    data: target,
  });
  return (
    <>
      {before}
      <li ref={setNodeRef} className={cn(ITEM_CHIP_CLASS, isOver && 'ring-2 ring-primary')}>
        <GameItemView
          item={placement.item}
          imageLabel={t('rooms.game.placedItemImage')}
          size="small"
        />
      </li>
    </>
  );
}
