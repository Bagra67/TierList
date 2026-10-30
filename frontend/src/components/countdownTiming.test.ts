import { describe, expect, it } from 'vitest';

import { COUNTDOWN_URGENT_SECONDS } from '../constants/rooms';
import { cooldownShakePx, isUrgent } from './countdownTiming';

describe('countdownTiming', () => {
  it('is urgent only in the last seconds, not once finished', () => {
    expect(isUrgent(COUNTDOWN_URGENT_SECONDS + 1)).toBe(false);
    expect(isUrgent(COUNTDOWN_URGENT_SECONDS)).toBe(true);
    expect(isUrgent(1)).toBe(true);
    expect(isUrgent(0)).toBe(false);
  });

  it('shakes the cooldown harder each second of the last seconds', () => {
    expect(cooldownShakePx(COUNTDOWN_URGENT_SECONDS + 1)).toBe(0);
    expect(cooldownShakePx(5)).toBe(1);
    expect(cooldownShakePx(4)).toBe(2);
    expect(cooldownShakePx(1)).toBe(5);
    expect(cooldownShakePx(0)).toBe(0);
  });
});
