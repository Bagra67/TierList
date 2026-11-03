import type { ReactNode } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { CurrentGame, Participant, Room } from '../api/rooms';
import { CooldownStage } from './CooldownStage';
import { CurrentItemCard } from './CurrentItemCard';
import { EndCooldownDialog } from './EndCooldownDialog';
import { GameAdminControls } from './GameAdminControls';
import { GameBoard } from './GameBoard';
import { PlacedList } from './PlacedList';
import { RoundHeader } from './RoundHeader';

interface GameScreenProps {
  room: Room;
  game: CurrentGame;
  onGameEnded: () => void;
}

export function GameScreen({ room, game, onGameEnded }: GameScreenProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const placingParticipants: Participant[] = room.participants.filter(
    (participant) => room.settings.admin_plays || !participant.is_admin,
  );
  const readerPlaces: boolean = placingParticipants.some((participant) => participant.is_you);

  if (game.status === 'cooldown') {
    const endCooldown: ReactNode = room.is_admin && (
      <EndCooldownDialog code={room.code} onEnded={onGameEnded} />
    );
    return (
      <CooldownStage
        room={room}
        game={game}
        readerPlaces={readerPlaces}
        endCooldown={endCooldown}
      />
    );
  }

  return (
    <section className="flex w-full flex-col gap-6">
      <h2 className="sr-only">{t('rooms.game.title')}</h2>
      <RoundHeader
        roundNumber={game.round_number}
        roundCount={game.round_count}
        endsAt={game.ends_at}
      />
      <div className="grid w-full items-start gap-6 lg:grid-cols-[minmax(0,1fr)_16rem]">
        {readerPlaces ? (
          <GameBoard room={room} game={game} />
        ) : (
          <CurrentItemCard item={game.current_item} />
        )}
        <aside className="flex flex-col gap-4">
          <PlacedList
            placingParticipants={placingParticipants}
            placedParticipantIds={game.placed_participant_ids}
          />
          {room.is_admin && <GameAdminControls room={room} />}
        </aside>
      </div>
    </section>
  );
}
