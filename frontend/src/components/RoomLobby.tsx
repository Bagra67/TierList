import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { Room } from '../api/rooms';
import { ErrorMessage } from './ErrorMessage';
import { RemoveParticipantDialog } from './RemoveParticipantDialog';
import { RoomBans } from './RoomBans';
import { RoomInvite } from './RoomInvite';
import { RoomSettingsDialog } from './RoomSettingsDialog';
import { RoomSettingsSummary } from './RoomSettingsSummary';
import { StartGameButton } from './StartGameButton';

interface RoomLobbyProps {
  room: Room;
}

// Lobby d'une salle (US-2.2, US-2.3) : code et lien à partager, participants (comptes et
// invités), réglages ; seul le room admin peut les modifier, et retirer ou bannir un participant
// (US-2.11, US-2.12)
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
      {room.game !== null && (
        <section className="flex w-full flex-col gap-2 rounded-lg bg-muted px-3 py-2">
          <p className="font-medium">{t('rooms.lobby.playing')}</p>
          {/* Écran de jeu provisoire : le vrai arrive avec #94 */}
          <p className="text-sm text-muted-foreground">
            {t('rooms.lobby.currentItem', {
              number: room.game.round_number,
              total: room.game.round_count,
            })}
          </p>
          {room.game.current_item.image_url !== null && (
            // Avec un texte, il est affiché juste en dessous : l'image est illustrative (alt vide),
            // sinon le lecteur d'écran le lirait deux fois
            <img
              src={room.game.current_item.image_url}
              alt={room.game.current_item.text === null ? t('rooms.lobby.currentItemImage') : ''}
              className="size-32 rounded-md object-cover"
            />
          )}
          {room.game.current_item.text !== null && (
            <p className="text-lg font-semibold">{room.game.current_item.text}</p>
          )}
        </section>
      )}
      {/* Sans template (purgé), le démarrage serait refusé : l'avertissement ci-dessus suffit */}
      {room.is_admin && room.game === null && room.template !== null && (
        <StartGameButton code={room.code} />
      )}
      <RoomInvite room={room} />
      <section className="flex w-full flex-col gap-2">
        <h2 className="text-lg font-semibold">
          {t('rooms.lobby.participants', { count: room.participants.length })}
        </h2>
        <ul className="flex w-full flex-col divide-y rounded-xl border">
          {room.participants.map((participant) => (
            <li key={participant.id} className="flex items-center gap-2 px-4 py-2">
              {/* Pleine en ligne, creuse hors ligne : la forme suffit, sans compter sur la couleur */}
              <span
                aria-hidden="true"
                className={
                  participant.connected
                    ? 'size-2.5 shrink-0 rounded-full bg-green-600'
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
              {/* Le room admin ne peut pas se retirer lui-même */}
              {room.is_admin && !participant.is_admin && (
                <RemoveParticipantDialog code={room.code} participant={participant} />
              )}
            </li>
          ))}
        </ul>
      </section>
      {room.is_admin && <RoomBans room={room} />}
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
