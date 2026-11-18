import { useEffect, useState } from 'react';

import { serverTimeMs } from '../api/serverClock';
import { COOLDOWN_SHAKE_STEP_PX, COUNTDOWN_URGENT_SECONDS } from '../constants/rooms';

const SECOND_MS = 1000;

function useServerTime(ticking: boolean): number {
  const [now, setNow] = useState<number>(() => serverTimeMs());

  useEffect(() => {
    if (!ticking) return undefined;
    const interval: number = window.setInterval(() => setNow(serverTimeMs()), SECOND_MS);
    return () => window.clearInterval(interval);
  }, [ticking]);

  return now;
}

function secondsUntil(endsAt: string, now: number): number {
  return Math.max(0, Math.ceil((Date.parse(endsAt) - now) / SECOND_MS));
}

export function useRemainingSeconds(endsAt: string): number {
  return secondsUntil(endsAt, useServerTime(true));
}

export function useRemainingSecondsIfTimed(endsAt: string | null): number | null {
  const now: number = useServerTime(endsAt !== null);
  return endsAt === null ? null : secondsUntil(endsAt, now);
}

export function isUrgent(remainingSeconds: number): boolean {
  return remainingSeconds > 0 && remainingSeconds <= COUNTDOWN_URGENT_SECONDS;
}

export function cooldownShakePx(remainingSeconds: number): number {
  if (!isUrgent(remainingSeconds)) return 0;
  return (COUNTDOWN_URGENT_SECONDS + 1 - remainingSeconds) * COOLDOWN_SHAKE_STEP_PX;
}
