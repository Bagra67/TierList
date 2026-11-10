import type { ClientRect } from '@dnd-kit/core';

import type { CurrentGame } from '../api/rooms';

export interface BoardDropTarget {
  tierId: string;
  itemId: string | null;
}

export type DropSide = 'before' | 'after';

export function dropSide(dragged: ClientRect | null, over: ClientRect): DropSide {
  if (dragged === null) return 'before';
  const draggedCenter: number = dragged.left + dragged.width / 2;
  const overCenter: number = over.left + over.width / 2;
  return draggedCenter > overCenter ? 'after' : 'before';
}

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

export function tierNameIn(game: CurrentGame, tierId: string): string {
  return game.tiers.find((tier) => tier.id === tierId)?.name ?? '';
}
