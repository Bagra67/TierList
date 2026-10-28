import { describe, expect, it } from 'vitest';

import { INK_TEXT_COLOR, WHITE_TEXT_COLOR } from '../constants/brand';
import { contrastRatio, readableTextColor } from './contrast';

describe('contrastRatio', () => {
  it('goes from 1 for the same color to 21 for black on white, in any order', () => {
    expect(contrastRatio('#777777', '#777777')).toBe(1);
    expect(contrastRatio('#000000', '#FFFFFF')).toBeCloseTo(21);
    expect(contrastRatio('#FFFFFF', '#000000')).toBeCloseTo(21);
  });
});

describe('readableTextColor', () => {
  it('writes in ink on light and saturated tier colors', () => {
    expect(readableTextColor('#FFC22E')).toBe(INK_TEXT_COLOR);
    expect(readableTextColor('#5B7CFA')).toBe(INK_TEXT_COLOR);
    expect(readableTextColor('#ffffff')).toBe(INK_TEXT_COLOR);
  });

  it('writes in white on dark colors', () => {
    expect(readableTextColor('#1D1640')).toBe(WHITE_TEXT_COLOR);
    expect(readableTextColor('#000000')).toBe(WHITE_TEXT_COLOR);
  });
});
