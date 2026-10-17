import type { ClientRect } from '@dnd-kit/core';

// Calculs du glisser-déposer des plateaux (GameBoard, CooldownBoard), sans React : le serveur
// attend le rang d'une tuile parmi les AUTRES tuiles du tier visé (docs/technical/games.md)

// Où une tuile serait posée : dans un tier, contre une tuile (itemId), ou à la fin (null)
export interface BoardDropTarget {
  tierId: string;
  itemId: string | null;
}

// Côté de la tuile survolée où tombe la tuile glissée
export type DropSide = 'before' | 'after';

// Après la tuile survolée si le centre de la tuile glissée a dépassé le sien, sinon avant
export function dropSide(dragged: ClientRect | null, over: ClientRect): DropSide {
  if (dragged === null) return 'before';
  const draggedCenter: number = dragged.left + dragged.width / 2;
  const overCenter: number = over.left + over.width / 2;
  return draggedCenter > overCenter ? 'after' : 'before';
}

// Rang à envoyer pour poser movingId sur la cible ; tierItemIds sont les tuiles du tier visé,
// dans l'ordre, movingId compris s'il y est déjà. null : la tuile resterait où elle est.
export function dropPosition(
  tierItemIds: readonly string[],
  movingId: string,
  target: BoardDropTarget,
  side: DropSide,
): number | null {
  if (target.itemId === movingId) return null;
  const others: string[] = tierItemIds.filter((id) => id !== movingId);
  const targetIndex: number = target.itemId === null ? -1 : others.indexOf(target.itemId);
  const position: number =
    targetIndex === -1 ? others.length : targetIndex + (side === 'after' ? 1 : 0);
  return tierItemIds.indexOf(movingId) === position ? null : position;
}
