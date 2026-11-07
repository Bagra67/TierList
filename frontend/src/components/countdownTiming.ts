import { useEffect, useState } from 'react';

import { COOLDOWN_SHAKE_STEP_PX, COUNTDOWN_URGENT_SECONDS } from '../constants/rooms';

const SECOND_MS = 1000;

export function useRemainingSeconds(endsAt: string): number {
  const [now, setNow] = useState<number>(() => Date.now());

  useEffect(() => {
    const interval: number = window.setInterval(() => setNow(Date.now()), SECOND_MS);
    return () => window.clearInterval(interval);
  }, []);

  return Math.max(0, Math.ceil((Date.parse(endsAt) - now) / SECOND_MS));
}

export function isUrgent(remainingSeconds: number): boolean {
  return remainingSeconds > 0 && remainingSeconds <= COUNTDOWN_URGENT_SECONDS;
}

export function cooldownShakePx(remainingSeconds: number): number {
  if (!isUrgent(remainingSeconds)) return 0;
  return (COUNTDOWN_URGENT_SECONDS + 1 - remainingSeconds) * COOLDOWN_SHAKE_STEP_PX;
}
