import {
  closestCenter,
  DndContext,
  KeyboardSensor,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type Announcements,
  type DragEndEvent,
  type SensorDescriptor,
  type SensorOptions,
} from '@dnd-kit/core';
import { CSS } from '@dnd-kit/utilities';
import { cn } from 'cn';
import type { CSSProperties, ReactNode } from 'react';
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
import { ErrorMessage } from './ErrorMessage';
import { GameItemView } from './GameItemView';
import { Button } from './ui/button';

// Où l'item en cours serait posé : un tier, et son rang parmi les autres items de ce tier
interface DropTarget {
  tierId: string;
  position: number;
}

const CURRENT_ITEM_ID = 'current-item';

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
  const sensors: SensorDescriptor<SensorOptions>[] = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor),
  );
  const currentItem: GameItem = game.current_item;
  const currentPlacement: OwnPlacement | undefined = game.own_placements.find(
    (placement) => placement.item.id === currentItem.id,
  );
  const itemLabel: string = currentItem.text ?? t('rooms.game.currentItemImage');

  // Les items d'un tier sans l'item en cours, dans l'ordre : les positions envoyées au serveur
  // sont des rangs parmi eux
  function othersIn(tierId: string): OwnPlacement[] {
    return game.own_placements.filter(
      (placement) => placement.tier_id === tierId && placement.item.id !== currentItem.id,
    );
  }

  function tierName(tierId: string): string {
    return game.tiers.find((tier) => tier.id === tierId)?.name ?? '';
  }

  async function placeAt(target: DropTarget) {
    try {
      await placeMutation.mutateAsync({
        tileId: currentItem.id,
        tierId: target.tierId,
        position: target.position,
      });
    } catch {
      return; // l'erreur est affichée depuis placeMutation.error
    }
  }

  function describe(target: DropTarget) {
    return { item: itemLabel, tier: tierName(target.tierId), position: target.position + 1 };
  }

  const announcements: Announcements = {
    onDragStart: () => t('rooms.game.dnd.pickedUp', { item: itemLabel }),
    onDragOver: ({ over }) =>
      over?.data.current === undefined
        ? undefined
        : t('rooms.game.dnd.over', describe(over.data.current as DropTarget)),
    onDragEnd: ({ over }) =>
      over?.data.current === undefined
        ? undefined
        : t('rooms.game.dnd.dropped', describe(over.data.current as DropTarget)),
    onDragCancel: () => t('rooms.game.dnd.cancelled', { item: itemLabel }),
  };

  function handleDragEnd({ over }: DragEndEvent) {
    if (over?.data.current === undefined) return;
    void placeAt(over.data.current as DropTarget);
  }

  return (
    <section className="flex w-full flex-col gap-3">
      <h2 className="text-lg font-semibold">{t('rooms.game.board')}</h2>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
        accessibility={{
          announcements,
          screenReaderInstructions: { draggable: t('rooms.game.dnd.instructions') },
        }}
      >
        {currentPlacement === undefined && (
          <div className="flex flex-col gap-2 rounded-lg border border-dashed p-3">
            <p className="text-sm text-muted-foreground">{t('rooms.game.dock')}</p>
            {/* L'item est affiché en grand au-dessus : ici, seulement la poignée à glisser */}
            <DraggableCurrentItem label={itemLabel} disabled={placeMutation.isPending}>
              {t('rooms.game.dragHandle')}
            </DraggableCurrentItem>
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
              itemLabel={itemLabel}
              pending={placeMutation.isPending}
              onPlace={(target) => void placeAt(target)}
            />
          ))}
        </ol>
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
  itemLabel: string;
  pending: boolean;
  onPlace: (target: DropTarget) => void;
}

function TierRow({
  tier,
  others,
  currentPlacement,
  currentItem,
  itemLabel,
  pending,
  onPlace,
}: TierRowProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  // Rang de l'item en cours parmi les autres items du tier : il est affiché avant others[rank]
  const currentRank: number | undefined = currentPlacement?.position;

  const currentChip = (
    <li className="flex items-center gap-1">
      <DraggableCurrentItem label={itemLabel} disabled={pending}>
        <GameItemView item={currentItem} imageLabel={itemLabel} size="small" />
      </DraggableCurrentItem>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        aria-label={t('rooms.game.moveEarlier', { item: itemLabel })}
        disabled={pending || currentRank === undefined || currentRank === 0}
        onClick={() => onPlace({ tierId: tier.id, position: (currentRank ?? 0) - 1 })}
      >
        ←
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        aria-label={t('rooms.game.moveLater', { item: itemLabel })}
        disabled={pending || currentRank === undefined || currentRank >= others.length}
        onClick={() => onPlace({ tierId: tier.id, position: (currentRank ?? 0) + 1 })}
      >
        →
      </Button>
    </li>
  );

  return (
    <li className="flex w-full flex-wrap items-center gap-2 rounded-lg border p-2">
      <span className="flex min-w-16 items-center gap-2 font-semibold">
        {/* La couleur accompagne le nom, qui suffit à lui seul */}
        <span
          aria-hidden="true"
          className="size-4 shrink-0 rounded-sm"
          style={{ backgroundColor: tier.color }}
        />
        {tier.name}
      </span>
      <ol className="flex flex-1 flex-wrap items-center gap-2" aria-label={tier.name}>
        {others.map((placement, index) => (
          <PlacedItemSlot
            key={placement.item.id}
            placement={placement}
            target={{ tierId: tier.id, position: index }}
            before={currentRank === index ? currentChip : null}
          />
        ))}
        {currentRank !== undefined && currentRank >= others.length && currentChip}
        <EndSlot target={{ tierId: tier.id, position: others.length }} />
      </ol>
      <Button
        type="button"
        variant="outline"
        size="sm"
        aria-label={t('rooms.game.placeInLabel', { tier: tier.name })}
        disabled={pending}
        onClick={() => onPlace({ tierId: tier.id, position: others.length })}
      >
        {t('rooms.game.placeIn', { tier: tier.name })}
      </Button>
    </li>
  );
}

interface PlacedItemSlotProps {
  placement: OwnPlacement;
  target: DropTarget;
  // L'item en cours, affiché juste avant cet item
  before: ReactNode;
}

// Un item d'un tour passé : il ne bouge pas, mais déposer l'item en cours dessus le place avant lui
function PlacedItemSlot({ placement, target, before }: PlacedItemSlotProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const { setNodeRef, isOver }: ReturnType<typeof useDroppable> = useDroppable({
    id: `${target.tierId}:${placement.item.id}`,
    data: target,
  });
  return (
    <>
      {before}
      <li
        ref={setNodeRef}
        className={cn(
          'rounded-md bg-muted px-2 py-1',
          // L'endroit où l'item tomberait : juste avant celui-ci
          isOver && 'border-l-4 border-dashed border-primary',
        )}
      >
        <GameItemView
          item={placement.item}
          imageLabel={t('rooms.game.placedItemImage')}
          size="small"
        />
      </li>
    </>
  );
}

// Fin d'un tier : déposer l'item en cours ici le place en dernier
function EndSlot({ target }: { target: DropTarget }) {
  const { setNodeRef, isOver }: ReturnType<typeof useDroppable> = useDroppable({
    id: `${target.tierId}:end`,
    data: target,
  });
  return (
    <li
      ref={setNodeRef}
      aria-hidden="true"
      className={cn(
        'h-10 w-12 rounded-md border-2 border-dashed border-muted-foreground/30',
        isOver && 'border-primary',
      )}
    />
  );
}

interface DraggableCurrentItemProps {
  label: string;
  disabled: boolean;
  children: ReactNode;
}

// L'item en cours, à glisser vers un tier ; le seul élément mobile du plateau
function DraggableCurrentItem({ label, disabled, children }: DraggableCurrentItemProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    isDragging,
  }: ReturnType<typeof useDraggable> = useDraggable({
    id: CURRENT_ITEM_ID,
    disabled,
  });
  const style: CSSProperties = {
    transform: CSS.Translate.toString(transform),
    zIndex: isDragging ? 1 : undefined,
    position: 'relative',
  };
  return (
    <button
      ref={setNodeRef}
      type="button"
      style={style}
      {...attributes}
      {...listeners}
      aria-label={t('rooms.game.dragLabel', { item: label })}
      className="cursor-grab touch-none rounded-md bg-primary/10 px-2 py-1 ring-2 ring-primary"
    >
      {children}
    </button>
  );
}
