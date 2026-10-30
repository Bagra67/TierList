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
import { GameItemView } from './GameItemView';

// Morceaux communs au plateau des tours (GameBoard) et au plateau du cooldown (CooldownBoard)

// Ce que porte une zone de dépôt, lu à la fin du glisser-déposer
type DropData = UseDroppableArguments['data'];

// Un nom de tier jusqu'à cette longueur (S, A+…) s'affiche en grand dans son bloc
const SHORT_TIER_NAME_LENGTH: number = 2;

interface TierLabelProps {
  tier: GameTier;
  // Pour nommer la ligne (aria-labelledby)
  id?: string;
  // Arrondi du coin gauche, quand la ligne est un cadre à elle seule (plateau, cooldown)
  className?: string;
}

// Bloc-lettre d'un tier, collé à gauche de sa ligne : le nom sur la couleur du tier. Le nom suffit
// à lui seul, la couleur l'accompagne. Un nom long est coupé après trois lignes (title le montre en
// entier, et le lecteur d'écran le lit en entier)
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
  // Nom accessible, quand le texte visible ne suffit pas (carte de l'élément en cours)
  ariaLabel?: string;
  // Clé pour useFocusAfterUpdate (boardHooks.ts)
  focusKey: string;
  disabled: boolean;
  // L'item à placer maintenant (tour en cours) : bordure de l'accent, pour le repérer
  emphasized?: boolean;
  // Autre forme que la puce (carte de l'élément en cours)
  className?: string;
  children: ReactNode;
}

// Un item à glisser vers un tier ; au clavier, Espace ou Entrée le saisit. Pendant le glisser, il
// reste à sa place, estompé : c'est son aperçu (DragPreview) qui suit le pointeur
export function DraggableItem({
  id,
  label,
  ariaLabel,
  focusKey,
  disabled,
  emphasized = false,
  className,
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
      className={cn(
        ITEM_CHIP_CLASS,
        // Le focus clavier (anneau) reste distinct de l'état au repos (bordure)
        'cursor-grab outline-none focus-visible:ring-3 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
        emphasized && EMPHASIZED_BORDER_CLASS,
        isDragging && 'opacity-40',
        className,
      )}
    >
      {children}
    </button>
  );
}

// Ce que montre l'aperçu d'un item glissé
export interface DragPreviewContent {
  item: GameItem;
  label: string;
  // Forme de la source (puce, puce d'accent, carte) : l'aperçu a sa taille, qui est aussi celle du
  // rectangle dont dnd-kit se sert pour viser le dépôt
  className: string;
  size: 'small' | 'large';
}

interface DragPreviewProps {
  // L'aperçu de l'item d'identifiant id, undefined s'il n'en a pas
  previewOf: (id: string) => DragPreviewContent | undefined;
}

// Aperçu de l'item glissé : une copie qui suit le pointeur (ou les flèches du clavier) au-dessus de
// tout le reste, avec l'ombre « projecteur ». Cachée aux lecteurs d'écran, qui ont déjà l'item et
// les annonces du glisser. Sans animation de dépôt : l'item apparaît à sa nouvelle place quand le
// serveur a répondu
export function DragPreview({ previewOf }: DragPreviewProps) {
  const { active }: ReturnType<typeof useDndContext> = useDndContext();
  const content: DragPreviewContent | undefined =
    active === null ? undefined : previewOf(String(active.id));
  return (
    <DragOverlay dropAnimation={null}>
      {content === undefined ? null : (
        <div
          aria-hidden="true"
          className={cn(content.className, 'cursor-grabbing shadow-lift motion-safe:-rotate-2')}
        >
          <GameItemView item={content.item} imageLabel={content.label} size={content.size} />
        </div>
      )}
    </DragOverlay>
  );
}
