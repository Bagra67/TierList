import { cn } from 'cn';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import type { PastGame, Room } from '../api/rooms';
import { type ResultsLinkState, resultsPath } from '../constants/routes';
import { panelVariants } from './ui/panel';
import { textLinkClassName } from './ui/text-link';

interface PastGamesProps {
  room: Room;
}

export function PastGames({ room }: PastGamesProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();

  if (room.past_games.length === 0) return null;

  return (
    <section className="flex w-full flex-col gap-2">
      <h2 className="text-lg font-semibold">
        {t('rooms.lobby.pastGames.title', { count: room.past_games.length })}
      </h2>
      <ul className={panelVariants({ variant: 'list' })}>
        {room.past_games.map((pastGame: PastGame) => {
          const closedAt: Date = new Date(pastGame.closed_at);
          return (
            <li key={pastGame.public_token} className="flex items-center gap-2 px-4 py-2">
              <span>{t('rooms.lobby.pastGames.closedAt', { date: closedAt })}</span>
              <span className="text-sm text-muted-foreground">
                {t('rooms.lobby.pastGames.players', { count: pastGame.player_count })}
              </span>
              <Link
                to={resultsPath(pastGame.public_token)}
                state={{ roomCode: room.code, isAdmin: room.is_admin } satisfies ResultsLinkState}
                aria-label={t('rooms.lobby.pastGames.openLabel', { date: closedAt })}
                className={cn(textLinkClassName, 'ml-auto text-sm')}
              >
                {t('rooms.lobby.pastGames.open')}
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
