import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import { Countdown } from './Countdown';

interface RoundHeaderProps {
  roundNumber: number;
  roundCount: number;
  // Fin du tour (minuteur), null sans minuteur
  endsAt: string | null;
}

// En-tête d'un tour : « Élément 5 sur 12 », la barre de progression de la partie et le chrono
export function RoundHeader({ roundNumber, roundCount, endsAt }: RoundHeaderProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const progress: string = t('rooms.game.itemProgress', {
    number: roundNumber,
    total: roundCount,
  });
  return (
    <div className="flex w-full flex-wrap items-center gap-x-6 gap-y-3">
      <p className="font-heading text-2xl font-black font-stretch-115%">{progress}</p>
      <div
        role="progressbar"
        aria-label={t('rooms.game.progress')}
        aria-valuemin={1}
        aria-valuemax={roundCount}
        aria-valuenow={roundNumber}
        aria-valuetext={progress}
        className="h-2 max-w-80 min-w-32 flex-1 overflow-hidden rounded-full bg-muted"
      >
        <div
          className="h-full rounded-full bg-foreground"
          style={{ width: `${(roundNumber / roundCount) * 100}%` }}
        />
      </div>
      {endsAt !== null && (
        <Countdown
          endsAt={endsAt}
          label={t('rooms.game.timeLeft')}
          variant="pill"
          className="ml-auto min-w-24"
        />
      )}
    </div>
  );
}
