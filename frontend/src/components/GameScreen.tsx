import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { CurrentGame, Participant, Room } from '../api/rooms';
import { CooldownBoard } from './CooldownBoard';
import { Countdown } from './Countdown';
import { EndCooldownDialog } from './EndCooldownDialog';
import { GameAdminControls } from './GameAdminControls';
import { GameBoard } from './GameBoard';
import { GameItemView } from './GameItemView';
import { PlacedList } from './PlacedList';
import { panelVariants } from './ui/panel';

interface GameScreenProps {
  room: Room;
  game: CurrentGame;
  // La partie est close par le room admin : le lobby reprend le focus
  onGameEnded: () => void;
}

// Écran d'une partie (US-3.2 à US-3.5) : l'item en cours et le temps restant, qui l'a placé, le
// plateau privé du lecteur s'il place les items, et les commandes du room admin. Le room admin qui
// ne joue pas a seulement les commandes, sans plateau. Pendant le cooldown final (US-4.1, US-4.6) :
// le bandeau et son compte à rebours, le plateau final, et « Terminer maintenant »
export function GameScreen({ room, game, onGameEnded }: GameScreenProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  // Le room admin qui ne joue pas ne place pas les items (US-3.5)
  const placingParticipants: Participant[] = room.participants.filter(
    (participant) => room.settings.admin_plays || !participant.is_admin,
  );
  const readerPlaces: boolean = placingParticipants.some((participant) => participant.is_you);

  if (game.status === 'cooldown') {
    return (
      // Le plateau télé du cooldown final (US-4.1) : sombre dans les deux thèmes, grâce à la
      // classe dark qui applique les jetons du thème sombre à tout ce qu'il contient
      <div className="dark flex w-full flex-col gap-4 rounded-[1rem] border bg-background p-4 text-foreground">
        <section className="flex w-full flex-col gap-1">
          <div className="flex flex-wrap items-center justify-between gap-x-4">
            <h2 className="text-2xl font-black [font-stretch:115%]">
              {t('rooms.game.cooldown.title')}
            </h2>
            {game.cooldown_ends_at !== null && (
              <Countdown
                endsAt={game.cooldown_ends_at}
                label={t('rooms.game.cooldown.timeLeft')}
                className="text-4xl font-black text-warning"
              />
            )}
          </div>
          <p className="text-sm text-muted-foreground">
            {readerPlaces ? t('rooms.game.cooldown.hint') : t('rooms.game.cooldown.waiting')}
          </p>
        </section>
        {readerPlaces && <CooldownBoard room={room} game={game} />}
        {room.is_admin && <EndCooldownDialog code={room.code} onEnded={onGameEnded} />}
      </div>
    );
  }

  return (
    <div className="flex w-full flex-col gap-4">
      <section className={panelVariants({ variant: 'muted' })}>
        <div className="flex items-center justify-between gap-4">
          <h2 className="font-medium">{t('rooms.game.title')}</h2>
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
