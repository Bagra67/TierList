import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { Room } from '../api/rooms';
import { ErrorMessage } from './ErrorMessage';
import { RoomInvite } from './RoomInvite';
import { RoomSettingsDialog } from './RoomSettingsDialog';
import { RoomSettingsSummary } from './RoomSettingsSummary';

interface RoomLobbyProps {
  room: Room;
}

// Lobby d'une salle (US-2.2, US-2.3) : code et lien à partager, participants (comptes et
// invités), réglages ; seul le room admin peut les modifier
export function RoomLobby({ room }: RoomLobbyProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();

  return (
    <>
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold">{t('rooms.lobby.title', { code: room.code })}</h1>
        {room.template !== null && (
          <p className="text-muted-foreground">
            {t('rooms.lobby.template', { name: room.template.name })}
          </p>
        )}
      </div>
      {room.template === null && <ErrorMessage>{t('rooms.lobby.templateDeleted')}</ErrorMessage>}
      {room.status === 'playing' && (
        <p className="rounded-lg bg-muted px-3 py-2 font-medium">{t('rooms.lobby.playing')}</p>
      )}
      <RoomInvite room={room} />
      <section className="flex w-full flex-col gap-2">
        <h2 className="text-lg font-semibold">
          {t('rooms.lobby.participants', { count: room.participants.length })}
        </h2>
        <ul className="flex w-full flex-col divide-y rounded-xl border">
          {room.participants.map((participant) => (
            <li key={participant.id} className="flex items-center gap-2 px-4 py-2">
              <span className="font-medium">{participant.display_name}</span>
              {participant.is_admin && (
                <span className="text-sm text-muted-foreground">({t('rooms.lobby.admin')})</span>
              )}
              {participant.is_guest && (
                <span className="text-sm text-muted-foreground">({t('rooms.lobby.guest')})</span>
              )}
            </li>
          ))}
        </ul>
      </section>
      <section className="flex w-full flex-col gap-2">
        <div className="flex w-full items-center justify-between gap-4">
          <h2 className="text-lg font-semibold">{t('rooms.settings.title')}</h2>
          {room.is_admin && <RoomSettingsDialog room={room} />}
        </div>
        <RoomSettingsSummary settings={room.settings} />
      </section>
    </>
  );
}
