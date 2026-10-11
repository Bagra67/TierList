import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { GuestRoom } from '../api/rooms';
import { CopyLinkField } from './CopyLinkField';

interface GuestLinkNoticeProps {
  guestRoom: GuestRoom;
}

// Lien perso d'un invité qui vient d'arriver (US-5.4) : il le ramène à sa place depuis
// n'importe quel appareil. Montré une seule fois : le serveur n'en garde que l'empreinte.
export function GuestLinkNotice({ guestRoom }: GuestLinkNoticeProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();

  return (
    <section className="flex w-full flex-col gap-2 rounded-xl border border-primary/40 p-4">
      <h2 className="font-semibold">{t('rooms.guestLink.title')}</h2>
      <p className="text-sm">
        {t('rooms.guestLink.hint', { date: new Date(guestRoom.guest_link_expires_at) })}
      </p>
      <CopyLinkField label={t('rooms.guestLink.label')} link={guestRoom.guest_link} />
    </section>
  );
}
