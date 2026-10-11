import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import { type GuestRoom, useRenewGuestLink } from '../api/rooms';
import { translateError } from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { GuestLinkNotice } from './GuestLinkNotice';
import { Button } from './ui/button';

interface GuestLinkSectionProps {
  code: string;
  // Lien perso connu de cette page (juste après l'arrivée ou un renouvellement), sinon null
  guestRoom: GuestRoom | null;
  onRenewed: (guestRoom: GuestRoom) => void;
}

// Lien perso d'un invité (US-5.4). Le serveur n'en garde que l'empreinte : après un rechargement,
// il n'est plus affichable, mais l'invité, reconnu par son cookie, peut en demander un nouveau.
export function GuestLinkSection({ code, guestRoom, onRenewed }: GuestLinkSectionProps) {
  const renewMutation = useRenewGuestLink(code);
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();

  if (guestRoom !== null) return <GuestLinkNotice guestRoom={guestRoom} />;

  async function renew() {
    let renewed: GuestRoom;
    try {
      renewed = await renewMutation.mutateAsync();
    } catch {
      return; // l'erreur est affichée depuis renewMutation.error
    }
    onRenewed(renewed);
  }

  return (
    <section className="flex w-full flex-col items-start gap-2 rounded-xl border p-4">
      <p className="text-sm text-muted-foreground">{t('rooms.guestLink.renewHint')}</p>
      <Button type="button" variant="outline" disabled={renewMutation.isPending} onClick={renew}>
        {renewMutation.isPending ? t('rooms.guestLink.renewing') : t('rooms.guestLink.renew')}
      </Button>
      {renewMutation.isError && (
        <ErrorMessage>{translateError(t, renewMutation.error)}</ErrorMessage>
      )}
    </section>
  );
}
