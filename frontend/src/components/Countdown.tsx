import { cn } from 'cn';

import { COUNTDOWN_URGENT_SECONDS } from '../constants/rooms';
import { useRemainingSeconds } from './countdownTiming';

interface CountdownProps {
  endsAt: string;
  label: string;
  variant?: 'text' | 'pill';
  className?: string;
}

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
