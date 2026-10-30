import {
  closestCenter,
  DndContext,
  useDroppable,
  type Announcements,
  type DragEndEvent,
} from '@dnd-kit/core';
import { cn } from 'cn';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import { type ReactNode, useRef } from 'react';
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
import {
  CURRENT_CARD_CLASS,
  CURRENT_CARD_IN_BOARD_CLASS,
  EMPHASIZED_BORDER_CLASS,
  ITEM_CHIP_CLASS,
} from './boardStyles';
import { CurrentItemCard } from './CurrentItemCard';
import {
  type DragPreviewContent,
  DragPreview,
  DraggableItem,
  EndSlot,
  TierLabel,
} from './gameBoardParts';
import { GameItemView } from './GameItemView';
import { Button } from './ui/button';

// Clés de focus de l'item en cours (useFocusAfterUpdate)
const CURRENT_FOCUS = { drag: 'current:drag', earlier: 'current:earlier', later: 'current:later' };

interface GameBoardProps {
  room: Room;
  game: CurrentGame;
}

// Le plateau privé du lecteur (US-3.3) : à gauche, la carte de l'élément en cours ; à droite, ses
// tiers et les items qu'il a déjà placés (ils ne bougent plus avant le cooldown). L'élément en cours
// se dépose dans un tier à la position voulue : à la souris ou au doigt en glissant sa carte ; au
// clavier par les boutons « Placer dans » et ←/→.
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

  // Seul l'élément en cours se glisse : un glisser commencé au tour précédent n'a pas d'aperçu.
  // L'aperçu a la forme de ce qu'on glisse : la carte tant qu'il n'est pas placé, sa puce ensuite
  function previewOf(id: string): DragPreviewContent | undefined {
    if (id !== draggableId) return undefined;
    if (currentPlacement === undefined) {
      return {
        item: currentItem,
        label: itemLabel,
        className: cn(ITEM_CHIP_CLASS, CURRENT_CARD_CLASS, EMPHASIZED_BORDER_CLASS),
        size: 'large',
      };
    }
    return {
      item: currentItem,
      label: itemLabel,
      className: cn(ITEM_CHIP_CLASS, EMPHASIZED_BORDER_CLASS),
      size: 'small',
    };
  }

  function handleDragEnd({ active, over }: DragEndEvent) {
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
    <section
      ref={sectionRef}
      className="grid w-full items-start gap-x-6 gap-y-3 lg:grid-cols-[12rem_minmax(0,1fr)]"
    >
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
        accessibility={{
          announcements,
          screenReaderInstructions: { draggable: t('rooms.game.dnd.instructions') },
        }}
      >
        <div className="flex flex-col items-center gap-3 lg:row-span-2">
          {/* Pas encore placé : la carte elle-même se glisse ; placé, elle reste en vue et c'est sa
              puce, dans le tier, qui bouge */}
          {currentPlacement === undefined ? (
            <DraggableItem
              id={draggableId}
              label={itemLabel}
              ariaLabel={t('rooms.game.dragHandleLabel', { item: itemLabel })}
              focusKey={CURRENT_FOCUS.drag}
              disabled={pending}
              emphasized
              className={cn(CURRENT_CARD_CLASS, CURRENT_CARD_IN_BOARD_CLASS)}
            >
              <GameItemView item={currentItem} imageLabel={itemLabel} size="large" />
            </DraggableItem>
          ) : (
            <CurrentItemCard item={currentItem} className={CURRENT_CARD_IN_BOARD_CLASS} />
          )}
          {currentPlacement === undefined && (
            <p className="text-sm text-muted-foreground">{t('rooms.game.dock')}</p>
          )}
        </div>
        <h2 className="text-lg font-semibold">{t('rooms.game.board')}</h2>
        <ol className="flex w-full flex-col gap-2 lg:col-start-2">
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
        <DragPreview previewOf={previewOf} />
      </DndContext>
      {placeMutation.isError && (
        <div className="lg:col-start-2">
          <ErrorMessage>{translateError(t, placeMutation.error)}</ErrorMessage>
        </div>
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
          sur la ligne, qui rognerait l'anneau de focus des tuiles */}
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
