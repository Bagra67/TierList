import { cn } from 'cn';
import type { CSSProperties, ReactNode } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { CurrentGame, Room } from '../api/rooms';
import { CooldownBoard } from './CooldownBoard';
import { Countdown } from './Countdown';
import { cooldownShakePx, useRemainingSeconds } from './countdownTiming';

interface CooldownStageProps {
  room: Room;
  game: CurrentGame;
  // Le lecteur place les items : il a le plateau final
  readerPlaces: boolean;
  // « Terminer maintenant », pour l'hôte (sinon rien)
  endCooldown: ReactNode;
}

// Le plateau télé du cooldown final (US-4.1) : sombre dans les deux thèmes, grâce à la classe dark
// qui applique les jetons du thème sombre à tout ce qu'il contient. La bordure jaune « projecteur »
// le détache aussi d'une page déjà sombre. Dans les dernières secondes, tout le bloc tremble, de
// plus en plus fort, et le chrono passe à l'accent (seule la couleur reste en mouvement réduit)
export function CooldownStage({ room, game, readerPlaces, endCooldown }: CooldownStageProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  // Sans heure de fin, le cooldown n'a pas de chrono, et ne tremble pas
  const remainingSeconds: number | null = useCooldownRemainingSeconds(game.cooldown_ends_at);
  const shakePx: number = remainingSeconds === null ? 0 : cooldownShakePx(remainingSeconds);
  // left / top, pas transform : un transform piégerait l'aperçu du glisser (position fixe)
  const shakeStyle: CSSProperties | undefined =
    shakePx > 0 ? ({ '--shake-px': `${shakePx}px` } as CSSProperties) : undefined;

  return (
    <div
      style={shakeStyle}
      className={cn(
        'dark relative flex w-full flex-col gap-4 rounded-panel border-2 border-warning/60 bg-background p-4 text-foreground',
        shakePx > 0 && 'motion-safe:animate-shake',
      )}
    >
      <section className="flex w-full flex-col gap-1">
        <div className="flex flex-wrap items-center justify-between gap-x-4">
          <h2 className="text-2xl font-black font-stretch-115%">
            {t('rooms.game.cooldown.title')}
          </h2>
          {game.cooldown_ends_at !== null && (
            <Countdown
              endsAt={game.cooldown_ends_at}
              label={t('rooms.game.cooldown.timeLeft')}
              className={cn('text-4xl font-black', shakePx > 0 ? 'text-primary' : 'text-warning')}
            />
          )}
        </div>
        <p className="text-sm text-muted-foreground">
          {readerPlaces ? t('rooms.game.cooldown.hint') : t('rooms.game.cooldown.waiting')}
        </p>
      </section>
      {/* Le lecteur qui place a le plateau, avec « Terminer maintenant » dans son panneau ;
          l'hôte qui ne joue pas n'a que ce bouton */}
      {readerPlaces ? <CooldownBoard room={room} game={game} aside={endCooldown} /> : endCooldown}
    </div>
  );
}

// useRemainingSeconds ne peut pas être appelé seulement quand l'heure de fin existe (règle des
// hooks) : sans heure de fin, il compte vers maintenant, et le résultat est ignoré
function useCooldownRemainingSeconds(endsAt: string | null): number | null {
  const remainingSeconds: number = useRemainingSeconds(endsAt ?? new Date(0).toISOString());
  return endsAt === null ? null : remainingSeconds;
}
