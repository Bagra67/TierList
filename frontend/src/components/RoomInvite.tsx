import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { Room } from '../api/rooms';
import { CopyLinkField } from './CopyLinkField';
import { panelVariants } from './ui/panel';
import { cn } from 'cn';

interface RoomInviteProps {
  room: Room;
}

// Code et lien de la salle à partager (US-2.3) : le lien convient à un message, le code à une
// lecture à voix haute
export function RoomInvite({ room }: RoomInviteProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();

  return (
    <section className={cn(panelVariants(), 'gap-4')}>
      <div className="flex flex-col gap-1">
        <h2 className="text-sm text-muted-foreground">{t('rooms.lobby.code')}</h2>
        <p className="font-mono text-3xl font-semibold tracking-widest">{room.code}</p>
      </div>
      <CopyLinkField label={t('rooms.lobby.link')} link={room.link} />
    </section>
  );
}
