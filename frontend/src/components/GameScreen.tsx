import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { CurrentGame, Participant, Room } from '../api/rooms';
import { Countdown } from './Countdown';
import { GameAdminControls } from './GameAdminControls';
import { GameBoard } from './GameBoard';
import { GameItemView } from './GameItemView';
import { PlacedList } from './PlacedList';

interface GameScreenProps {
  room: Room;
  game: CurrentGame;
}

// Écran d'une partie (US-3.2 à US-3.5) : l'item en cours et le temps restant, qui l'a placé, le
// plateau privé du lecteur s'il place les items, et les commandes du room admin. Le room admin qui
// ne joue pas a seulement les commandes, sans plateau
export function GameScreen({ room, game }: GameScreenProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  // Le room admin qui ne joue pas ne place pas les items (US-3.5)
  const placingParticipants: Participant[] = room.participants.filter(
    (participant) => room.settings.admin_plays || !participant.is_admin,
  );
  const readerPlaces: boolean = placingParticipants.some((participant) => participant.is_you);

  if (game.status === 'cooldown') {
    return (
      <section className="flex w-full flex-col gap-2 rounded-lg bg-muted px-3 py-2">
        <p className="font-medium">{t('rooms.game.title')}</p>
        <p role="status">{t('rooms.game.cooldown')}</p>
        {game.cooldown_ends_at !== null && (
          <Countdown endsAt={game.cooldown_ends_at} label={t('rooms.game.cooldownLeft')} />
        )}
      </section>
    );
  }

  return (
    <div className="flex w-full flex-col gap-4">
      <section className="flex w-full flex-col gap-2 rounded-lg bg-muted px-3 py-2">
        <div className="flex items-center justify-between gap-4">
          <p className="font-medium">{t('rooms.game.title')}</p>
          {game.ends_at !== null && (
            <Countdown endsAt={game.ends_at} label={t('rooms.game.timeLeft')} />
          )}
        </div>
        <p className="text-sm text-muted-foreground">
          {t('rooms.game.itemProgress', { number: game.round_number, total: game.round_count })}
        </p>
        <GameItemView
          item={game.current_item}
          imageLabel={t('rooms.game.currentItemImage')}
          size="large"
        />
      </section>
      <PlacedList
        placingParticipants={placingParticipants}
        placedParticipantIds={game.placed_participant_ids}
      />
      {readerPlaces && <GameBoard room={room} game={game} />}
      {room.is_admin && <GameAdminControls room={room} />}
    </div>
  );
}
