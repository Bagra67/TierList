import { cn } from 'cn';

import { COUNTDOWN_URGENT_SECONDS } from '../constants/rooms';
import { useRemainingSeconds } from './countdownTiming';

interface CountdownProps {
  // Fin décidée par le serveur (ISO 8601, UTC)
  endsAt: string;
  // Ce qui se termine, lu par les lecteurs d'écran (« Temps restant »)
  label: string;
  // text : le chiffre seul ; pill : une pastille jaune « projecteur », qui passe à l'accent dans
  // les dernières secondes (chrono de la manche)
  variant?: 'text' | 'pill';
  // Taille et couleur selon l'endroit (chrono jaune du cooldown)
  className?: string;
}

// Compte à rebours calculé localement depuis l'heure de fin du serveur (docs/technical/realtime.md) ;
// role="timer" : les lecteurs d'écran ne l'annoncent pas à chaque seconde
export function Countdown({ endsAt, label, variant = 'text', className }: CountdownProps) {
  const remainingSeconds: number = useRemainingSeconds(endsAt);
  const minutes: number = Math.floor(remainingSeconds / 60);
  const seconds: string = String(remainingSeconds % 60).padStart(2, '0');

  return (
    <p
      role="timer"
      aria-label={label}
      className={cn(
        'font-heading text-lg font-bold tabular-nums',
        variant === 'pill' && 'rounded-full px-4 py-1 text-center text-2xl font-black',
        variant === 'pill' &&
          (remainingSeconds <= COUNTDOWN_URGENT_SECONDS
            ? 'bg-primary text-primary-foreground'
            : 'bg-spotlight text-spotlight-foreground'),
        className,
      )}
    >
      {minutes}:{seconds}
    </p>
  );
}
