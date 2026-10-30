import { cn } from 'cn';
import { type ChangeEvent, useId } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import { type Room, useNextRound, useUpdateRoomSettings } from '../api/rooms';
import { translateError } from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { Button } from './ui/button';
import { panelVariants } from './ui/panel';

interface GameAdminControlsProps {
  room: Room;
}

// Commandes du room admin pendant un tour (US-3.4, US-2.10) : « Item suivant » est toujours
// possible, quel que soit le réglage automatique ; les arrivées peuvent être ouvertes ou fermées
export function GameAdminControls({ room }: GameAdminControlsProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const nextMutation = useNextRound(room.code);
  const settingsMutation = useUpdateRoomSettings(room.code);
  const arrivalsId: string = useId();
  const headingId: string = useId();

  async function handleNext() {
    try {
      await nextMutation.mutateAsync();
    } catch {
      return; // l'erreur est affichée depuis nextMutation.error
    }
  }

  async function handleArrivals(event: ChangeEvent<HTMLInputElement>) {
    try {
      await settingsMutation.mutateAsync({ late_arrivals_allowed: event.target.checked });
    } catch {
      return; // l'erreur est affichée depuis settingsMutation.error
    }
  }

  // Encadré bordé de jaune « projecteur » : les commandes de l'hôte se repèrent d'un coup d'œil
  return (
    <section
      aria-labelledby={headingId}
      className={cn(panelVariants(), 'border-2 border-spotlight')}
    >
      <h3 id={headingId} className="font-semibold">
        {t('rooms.game.hostControls')}
      </h3>
      <div className="flex flex-wrap items-center gap-3">
        <Button type="button" onClick={handleNext} disabled={nextMutation.isPending}>
          {nextMutation.isPending ? t('rooms.game.nexting') : t('rooms.game.next')}
        </Button>
        <p className="text-sm text-muted-foreground">
          {t(`rooms.game.auto.${room.settings.auto_advance}`, {
            seconds: room.settings.timer_seconds,
          })}
        </p>
      </div>
      <div className="flex items-center gap-2">
        <input
          id={arrivalsId}
          type="checkbox"
          checked={room.settings.late_arrivals_allowed}
          disabled={settingsMutation.isPending}
          onChange={handleArrivals}
        />
        <label htmlFor={arrivalsId}>{t('rooms.game.lateArrivals')}</label>
      </div>
      {nextMutation.isError && <ErrorMessage>{translateError(t, nextMutation.error)}</ErrorMessage>}
      {settingsMutation.isError && (
        <ErrorMessage>{translateError(t, settingsMutation.error)}</ErrorMessage>
      )}
    </section>
  );
}
