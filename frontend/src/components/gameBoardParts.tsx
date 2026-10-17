import { type UseDroppableArguments, useDraggable, useDroppable } from '@dnd-kit/core';
import { CSS } from '@dnd-kit/utilities';
import { cn } from 'cn';
import type { CSSProperties, ReactNode } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { GameTier } from '../api/rooms';

// Morceaux communs au plateau des tours (GameBoard) et au plateau du cooldown (CooldownBoard)

// Ce que porte une zone de dépôt, lu à la fin du glisser-déposer
type DropData = UseDroppableArguments['data'];

// Pastille de couleur et nom d'un tier ; la couleur accompagne le nom, qui suffit à lui seul
export function TierLabel({ tier }: { tier: GameTier }) {
  return (
    <span className="flex min-w-16 items-center gap-2 font-semibold">
      <span
        aria-hidden="true"
        className="size-4 shrink-0 rounded-sm"
        style={{ backgroundColor: tier.color }}
      />
      {tier.name}
    </span>
  );
}

interface EndSlotProps {
  id: string;
  data: DropData;
}

// Fin d'un tier : déposer un item ici le place en dernier
export function EndSlot({ id, data }: EndSlotProps) {
  const { setNodeRef, isOver }: ReturnType<typeof useDroppable> = useDroppable({ id, data });
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

interface DraggableItemProps {
  // Identifiant du glisser-déposer : event.active.id à la fin
  id: string;
  label: string;
  disabled: boolean;
  children: ReactNode;
}

// Un item à glisser vers un tier ; au clavier, Espace ou Entrée le saisit
export function DraggableItem({ id, label, disabled, children }: DraggableItemProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    isDragging,
  }: ReturnType<typeof useDraggable> = useDraggable({ id, disabled });
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
