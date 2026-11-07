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
  readerPlaces: boolean;
  endCooldown: ReactNode;
}

export function CooldownStage({ room, game, readerPlaces, endCooldown }: CooldownStageProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const remainingSeconds: number | null = useCooldownRemainingSeconds(game.cooldown_ends_at);
  const shakePx: number = remainingSeconds === null ? 0 : cooldownShakePx(remainingSeconds);
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
      {readerPlaces ? <CooldownBoard room={room} game={game} aside={endCooldown} /> : endCooldown}
    </div>
  );
}

const NO_END_TIME_PLACEHOLDER: string = new Date(0).toISOString();

function useCooldownRemainingSeconds(endsAt: string | null): number | null {
  const remainingSeconds: number = useRemainingSeconds(endsAt ?? NO_END_TIME_PLACEHOLDER);
  return endsAt === null ? null : remainingSeconds;
}
