import { type UseDroppableArguments, useDraggable, useDroppable } from '@dnd-kit/core';
import { CSS } from '@dnd-kit/utilities';
import { cn } from 'cn';
import type { CSSProperties, ReactNode } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { GameTier } from '../api/rooms';
import { ITEM_CHIP_CLASS, tierColorStyle } from './boardStyles';

// Morceaux communs au plateau des tours (GameBoard) et au plateau du cooldown (CooldownBoard)

// Ce que porte une zone de dépôt, lu à la fin du glisser-déposer
type DropData = UseDroppableArguments['data'];

// Un nom de tier jusqu'à cette longueur (S, A+…) s'affiche en grand dans son bloc
const SHORT_TIER_NAME_LENGTH: number = 2;

interface TierLabelProps {
  tier: GameTier;
  // Pour nommer la ligne (aria-labelledby)
  id?: string;
}

// Bloc-lettre d'un tier, collé à gauche de sa ligne : le nom sur la couleur du tier. Le nom suffit
// à lui seul, la couleur l'accompagne
export function TierLabel({ tier, id }: TierLabelProps) {
  return (
    <span
      id={id}
      style={tierColorStyle(tier.color)}
      className={cn(
        'flex min-h-14 w-16 shrink-0 items-center justify-center self-stretch px-1 text-center font-heading font-black wrap-anywhere [font-stretch:125%] sm:min-h-16 sm:w-20',
        tier.name.length <= SHORT_TIER_NAME_LENGTH ? 'text-3xl' : 'text-sm',
      )}
    >
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
        'h-14 w-12 rounded-md border-2 border-dashed border-muted-foreground/30 sm:h-16',
        isOver && 'border-primary',
      )}
    />
  );
}

interface DraggableItemProps {
  // Identifiant du glisser-déposer : event.active.id à la fin
  id: string;
  label: string;
  // Nom accessible, quand le texte visible n'est pas l'item lui-même (poignée du dock)
  ariaLabel?: string;
  // Clé pour useFocusAfterUpdate (boardHooks.ts)
  focusKey: string;
  disabled: boolean;
  // L'item à placer maintenant (tour en cours) : bordure de l'accent, pour le repérer
  emphasized?: boolean;
  children: ReactNode;
}

// Un item à glisser vers un tier ; au clavier, Espace ou Entrée le saisit
export function DraggableItem({
  id,
  label,
  ariaLabel,
  focusKey,
  disabled,
  emphasized = false,
  children,
}: DraggableItemProps) {
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
      data-focus-key={focusKey}
      aria-label={ariaLabel ?? t('rooms.game.dragLabel', { item: label })}
      className={cn(
        ITEM_CHIP_CLASS,
        // Le focus clavier (anneau) reste distinct de l'état au repos (bordure)
        'cursor-grab outline-none focus-visible:ring-3 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
        emphasized && 'border-2 border-primary',
        isDragging && 'cursor-grabbing shadow-lift',
      )}
    >
      {children}
    </button>
  );
}
