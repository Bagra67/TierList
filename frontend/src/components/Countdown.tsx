import { useEffect, useState } from 'react';
import { cn } from 'cn';

interface CountdownProps {
  // Fin décidée par le serveur (ISO 8601, UTC)
  endsAt: string;
  // Ce qui se termine, lu par les lecteurs d'écran (« Temps restant »)
  label: string;
  // Taille et couleur selon l'endroit (chrono jaune du cooldown)
  className?: string;
}

const SECOND_MS = 1000;

// Compte à rebours calculé localement depuis l'heure de fin du serveur (docs/technical/realtime.md) ;
// role="timer" : les lecteurs d'écran ne l'annoncent pas à chaque seconde
export function Countdown({ endsAt, label, className }: CountdownProps) {
  const [now, setNow] = useState<number>(() => Date.now());

  useEffect(() => {
    const interval: number = window.setInterval(() => setNow(Date.now()), SECOND_MS);
    return () => window.clearInterval(interval);
  }, []);

  const remainingSeconds: number = Math.max(0, Math.ceil((Date.parse(endsAt) - now) / SECOND_MS));
  const minutes: number = Math.floor(remainingSeconds / 60);
  const seconds: string = String(remainingSeconds % 60).padStart(2, '0');

  return (
    <p
      role="timer"
      aria-label={label}
      className={cn('font-heading text-lg font-bold tabular-nums', className)}
    >
      {minutes}:{seconds}
    </p>
  );
}
