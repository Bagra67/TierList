import { cn } from 'cn';
import { useRef } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { Room } from '../api/rooms';
import { CONTENT_COLUMN_CLASS } from '../constants/layout';
import { CloseRoomDialog } from './CloseRoomDialog';
import { ErrorMessage } from './ErrorMessage';
import { GameScreen } from './GameScreen';
import { PastGames } from './PastGames';
import { RemoveParticipantDialog } from './RemoveParticipantDialog';
import { RoomBans } from './RoomBans';
import { RoomInvite } from './RoomInvite';
import { RoomSettingsDialog } from './RoomSettingsDialog';
import { RoomSettingsSummary } from './RoomSettingsSummary';
import { StartGameButton } from './StartGameButton';
import { panelVariants } from './ui/panel';

interface RoomLobbyProps {
  room: Room;
}

export function RoomLobby({ room }: RoomLobbyProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const headingRef = useRef<HTMLHeadingElement>(null);

  return (
    <>
      <div className="flex flex-col gap-1">
        <h1 ref={headingRef} tabIndex={-1} className="text-2xl font-semibold outline-none">
          {t('rooms.lobby.title', { code: room.code })}
        </h1>
        {room.template !== null && (
          <p className="text-muted-foreground">
            {t('rooms.lobby.template', { name: room.template.name })}
          </p>
        )}
      </div>
      {room.template === null && <ErrorMessage>{t('rooms.lobby.templateDeleted')}</ErrorMessage>}
      {room.template?.hidden === true && (
        <ErrorMessage>{t('rooms.lobby.templateHidden')}</ErrorMessage>
      )}
      {room.game !== null && (
        <GameScreen room={room} game={room.game} onGameEnded={() => headingRef.current?.focus()} />
      )}
      <div className={cn(CONTENT_COLUMN_CLASS, 'flex flex-col items-start gap-6')}>
        {room.is_admin && room.game === null && room.template !== null && !room.template.hidden && (
          <StartGameButton code={room.code} replay={room.past_games.length > 0} />
        )}
        <RoomInvite room={room} />
        <section className="flex w-full flex-col gap-2">
          <h2 className="text-lg font-semibold">
            {t('rooms.lobby.participants', { count: room.participants.length })}
          </h2>
          <ul className={panelVariants({ variant: 'list' })}>
            {room.participants.map((participant) => (
              <li key={participant.id} className="flex items-center gap-2 px-4 py-2">
                <span
                  aria-hidden="true"
                  className={
                    participant.connected
                      ? 'size-2.5 shrink-0 rounded-full bg-success'
                      : 'size-2.5 shrink-0 rounded-full border-2 border-muted-foreground'
                  }
                />
                <span className="sr-only">
                  {participant.connected ? t('rooms.lobby.online') : t('rooms.lobby.offline')}
                </span>
                <span className="font-medium">{participant.display_name}</span>
                {participant.is_admin && (
                  <span className="text-sm text-muted-foreground">({t('rooms.lobby.admin')})</span>
                )}
                {participant.is_guest && (
                  <span className="text-sm text-muted-foreground">({t('rooms.lobby.guest')})</span>
                )}
                {room.is_admin && !participant.is_admin && (
                  <RemoveParticipantDialog code={room.code} participant={participant} />
                )}
              </li>
            ))}
          </ul>
        </section>
        <PastGames room={room} />
        {room.is_admin && <RoomBans room={room} />}
        <section className="flex w-full flex-col gap-2">
          <div className="flex w-full items-center justify-between gap-4">
            <h2 className="text-lg font-semibold">{t('rooms.settings.title')}</h2>
            {room.is_admin && <RoomSettingsDialog room={room} />}
          </div>
          <RoomSettingsSummary settings={room.settings} />
        </section>
        {room.is_admin && <CloseRoomDialog code={room.code} gameInProgress={room.game !== null} />}
      </div>
    </>
  );
}
