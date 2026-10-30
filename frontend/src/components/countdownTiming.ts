import { useEffect, useState } from 'react';

import { COOLDOWN_SHAKE_STEP_PX, COUNTDOWN_URGENT_SECONDS } from '../constants/rooms';

const SECOND_MS = 1000;

// Secondes restantes avant endsAt (fin décidée par le serveur, ISO 8601), recalculées chaque
// seconde à partir de l'horloge locale (docs/technical/realtime.md) ; jamais négatives
export function useRemainingSeconds(endsAt: string): number {
  const [now, setNow] = useState<number>(() => Date.now());

  useEffect(() => {
    const interval: number = window.setInterval(() => setNow(Date.now()), SECOND_MS);
    return () => window.clearInterval(interval);
  }, []);

  return Math.max(0, Math.ceil((Date.parse(endsAt) - now) / SECOND_MS));
}

// Les dernières secondes : le chrono passe à l'accent (et le cooldown tremble). À 0, c'est fini
export function isUrgent(remainingSeconds: number): boolean {
  return remainingSeconds > 0 && remainingSeconds <= COUNTDOWN_URGENT_SECONDS;
}

// Amplitude du tremblement du cooldown, en pixels : elle grandit de COOLDOWN_SHAKE_STEP_PX à chaque
// seconde (0,5 px à COUNTDOWN_URGENT_SECONDS, 2,5 px à la dernière) ; 0 hors des dernières secondes
export function cooldownShakePx(remainingSeconds: number): number {
  if (!isUrgent(remainingSeconds)) return 0;
  return (COUNTDOWN_URGENT_SECONDS + 1 - remainingSeconds) * COOLDOWN_SHAKE_STEP_PX;
}
