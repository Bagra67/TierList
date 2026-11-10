import type { ReactNode } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { CurrentGame, Room } from '../api/rooms';
import { CooldownBoard } from './CooldownBoard';
import { CooldownFrame } from './CooldownFrame';

interface CooldownStageProps {
  room: Room;
  game: CurrentGame;
  readerPlaces: boolean;
  endCooldown: ReactNode;
}

export function CooldownStage({ room, game, readerPlaces, endCooldown }: CooldownStageProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();

  return (
    <CooldownFrame
      endsAt={game.cooldown_ends_at}
      hint={readerPlaces ? t('rooms.game.cooldown.hint') : t('rooms.game.cooldown.waiting')}
    >
      {readerPlaces ? <CooldownBoard room={room} game={game} aside={endCooldown} /> : endCooldown}
    </CooldownFrame>
  );
}
