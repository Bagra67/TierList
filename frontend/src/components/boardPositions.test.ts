import type { ClientRect } from '@dnd-kit/core';
import { describe, expect, it } from 'vitest';

import { dropPosition, dropSide } from './boardPositions';

function rect(left: number, width: number): ClientRect {
  return { left, width, top: 0, height: 40, right: left + width, bottom: 40 };
}

describe('dropPosition', () => {
  const tierS: string[] = ['A', 'B', 'C'];

  it('keeps a tile dropped on itself where it is', () => {
    expect(dropPosition(tierS, 'B', { tierId: 'S', itemId: 'B' }, 'after')).toBeNull();
  });

  it('moves a tile before or after a tile of its own tier', () => {
    expect(dropPosition(tierS, 'A', { tierId: 'S', itemId: 'C' }, 'before')).toBe(1);
    expect(dropPosition(tierS, 'C', { tierId: 'S', itemId: 'A' }, 'before')).toBe(0);
  });

  it('counts the rank once the moved tile has left its tier', () => {
    const rankOfAAfterBOnceBIsFirst: number = 1;

    expect(dropPosition(tierS, 'A', { tierId: 'S', itemId: 'B' }, 'after')).toBe(
      rankOfAAfterBOnceBIsFirst,
    );
  });

  it('ignores a drop that would leave the tile in place', () => {
    expect(dropPosition(tierS, 'A', { tierId: 'S', itemId: 'B' }, 'before')).toBeNull();
    expect(dropPosition(tierS, 'C', { tierId: 'S', itemId: null }, 'before')).toBeNull();
  });

  it('places a tile of another tier, or a missed item, against a tile or at the end', () => {
    expect(dropPosition(tierS, 'X', { tierId: 'S', itemId: 'B' }, 'before')).toBe(1);
    expect(dropPosition(tierS, 'X', { tierId: 'S', itemId: 'B' }, 'after')).toBe(2);
    expect(dropPosition(tierS, 'X', { tierId: 'S', itemId: null }, 'before')).toBe(3);
    expect(dropPosition([], 'X', { tierId: 'A', itemId: null }, 'before')).toBe(0);
  });
});

describe('dropSide', () => {
  it('drops after the hovered tile once the dragged centre has passed its centre', () => {
    expect(dropSide(rect(130, 40), rect(100, 60))).toBe('after');
    expect(dropSide(rect(90, 40), rect(100, 60))).toBe('before');
  });

  it('drops before when the dragged position is unknown', () => {
    expect(dropSide(null, rect(100, 60))).toBe('before');
  });
});
