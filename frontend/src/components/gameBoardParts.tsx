import {
  DragOverlay,
  type UseDroppableArguments,
  useDndContext,
  useDraggable,
  useDroppable,
} from '@dnd-kit/core';
import { cn } from 'cn';
import type { ReactNode } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { GameItem, GameTier } from '../api/rooms';
import {
  EMPHASIZED_BORDER_CLASS,
  ITEM_CHIP_CLASS,
  TIER_LABEL_CLASS,
  tierColorStyle,
} from './boardStyles';
import { tileFocusKey } from './boardHooks';
import { GameItemView } from './GameItemView';

type DropData = UseDroppableArguments['data'];

const SHORT_TIER_NAME_LENGTH: number = 2;

interface TierLabelProps {
  tier: GameTier;
  id?: string;
  className?: string;
}

export function TierLabel({ tier, id, className }: TierLabelProps) {
  return (
    <span
      id={id}
      title={tier.name}
      style={tierColorStyle(tier.color)}
      className={cn(
        TIER_LABEL_CLASS,
        'font-heading font-black wrap-anywhere font-stretch-125%',
        tier.name.length <= SHORT_TIER_NAME_LENGTH ? 'text-3xl' : 'text-sm',
        className,
      )}
    >
      <span className="line-clamp-3">{tier.name}</span>
    </span>
  );
}

interface EndSlotProps {
  id: string;
  data: DropData;
}

export function EndSlot({ id, data }: EndSlotProps) {
  const { setNodeRef, isOver }: ReturnType<typeof useDroppable> = useDroppable({ id, data });
  return (
    <li
      ref={setNodeRef}
      aria-hidden="true"
      className={cn(
        'h-14 w-12 rounded-md border-2 border-dashed border-muted-foreground/30 sm:h-16',
        isOver && 'border-primary',
      )}
    />
  );
}

interface DraggableItemProps {
  id: string;
  label: string;
  ariaLabel?: string;
  focusKey: string;
  disabled: boolean;
  emphasized?: boolean;
  className?: string;
  onClick?: () => void;
  pressed?: boolean;
  children: ReactNode;
}

export function DraggableItem({
  id,
  label,
  ariaLabel,
  focusKey,
  disabled,
  emphasized = false,
  className,
  onClick,
  pressed,
  children,
}: DraggableItemProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const { attributes, listeners, setNodeRef, isDragging }: ReturnType<typeof useDraggable> =
    useDraggable({ id, disabled });
  return (
    <button
      ref={setNodeRef}
      type="button"
      {...attributes}
      {...listeners}
      data-focus-key={focusKey}
      aria-label={ariaLabel ?? t('rooms.game.dragLabel', { item: label })}
      aria-pressed={pressed}
      onClick={onClick}
      className={cn(
        ITEM_CHIP_CLASS,
        'cursor-grab outline-none focus-visible:ring-3 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
        emphasized && EMPHASIZED_BORDER_CLASS,
        pressed && 'ring-3 ring-primary',
        isDragging && 'opacity-40',
        className,
      )}
    >
      {children}
    </button>
  );
}

export interface DragPreviewContent {
  item: GameItem;
  label: string;
  sourceShapeClassName: string;
  size: 'small' | 'large';
}

interface DragPreviewProps {
  previewOf: (id: string) => DragPreviewContent | undefined;
}

export function DragPreview({ previewOf }: DragPreviewProps) {
  const { active }: ReturnType<typeof useDndContext> = useDndContext();
  const content: DragPreviewContent | undefined =
    active === null ? undefined : previewOf(String(active.id));
  return (
    <DragOverlay dropAnimation={null}>
      {content === undefined ? null : (
        <div
          aria-hidden="true"
          className={cn(
            content.sourceShapeClassName,
            'cursor-grabbing shadow-lift motion-safe:-rotate-2',
          )}
        >
          <GameItemView item={content.item} imageLabel={content.label} size={content.size} />
        </div>
      )}
    </DragOverlay>
  );
}

interface ChoosableTileProps {
  item: GameItem;
  label: string;
  chosen: boolean;
  pending: boolean;
  onChoose: (itemId: string) => void;
}

export function ChoosableTile({ item, label, chosen, pending, onChoose }: ChoosableTileProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  return (
    <DraggableItem
      id={item.id}
      label={label}
      ariaLabel={t('rooms.game.cooldown.chooseLabel', { item: label })}
      focusKey={tileFocusKey(item.id)}
      disabled={pending}
      pressed={chosen}
      onClick={() => onChoose(item.id)}
    >
      <GameItemView item={item} imageLabel={label} size="small" />
    </DraggableItem>
  );
}
