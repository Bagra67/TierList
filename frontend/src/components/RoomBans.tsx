import { useTranslation } from 'react-i18next';

import { type Room, type RoomBan, useUnban } from '../api/rooms';
import { translateError } from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { Button } from './ui/button';

interface RoomBansProps {
  room: Room;
}

// Personnes bannies de la salle (US-2.12), que le room admin peut débannir. Le backend n'envoie
// cette liste qu'au room admin ; vide, rien n'est affiché.
export function RoomBans({ room }: RoomBansProps) {
  const unbanMutation = useUnban(room.code);
  const { t } = useTranslation();

  if (room.bans.length === 0) return null;

  return (
    <section className="flex w-full flex-col gap-2">
      <h2 className="text-lg font-semibold">
        {t('rooms.lobby.bans.title', { count: room.bans.length })}
      </h2>
      {unbanMutation.isError && (
        <ErrorMessage>{translateError(t, unbanMutation.error)}</ErrorMessage>
      )}
      <ul className="flex w-full flex-col divide-y rounded-xl border">
        {room.bans.map((roomBan: RoomBan) => (
          <li key={roomBan.id} className="flex items-center gap-2 px-4 py-2">
            <span className="font-medium">{roomBan.display_name}</span>
            {roomBan.is_guest && (
              <span className="text-sm text-muted-foreground">({t('rooms.lobby.guest')})</span>
            )}
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="ml-auto"
              disabled={unbanMutation.isPending}
              aria-label={t('rooms.lobby.bans.unbanLabel', { name: roomBan.display_name })}
              onClick={() => unbanMutation.mutate(roomBan.id)}
            >
              {t('rooms.lobby.bans.unban')}
            </Button>
          </li>
        ))}
      </ul>
    </section>
  );
}
