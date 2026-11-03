import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import { type GuestRoom, useRenewGuestLink } from '../api/rooms';
import { translateError } from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { GuestLinkNotice } from './GuestLinkNotice';
import { Button } from './ui/button';
import { panelVariants } from './ui/panel';
import { cn } from 'cn';

interface GuestLinkSectionProps {
  code: string;
  justIssuedGuestLink: GuestRoom | null;
  onRenewed: (guestRoom: GuestRoom) => void;
}

export function GuestLinkSection({ code, justIssuedGuestLink, onRenewed }: GuestLinkSectionProps) {
  const renewMutation = useRenewGuestLink(code);
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();

  if (justIssuedGuestLink !== null) return <GuestLinkNotice guestRoom={justIssuedGuestLink} />;

  async function renew() {
    let renewed: GuestRoom;
    try {
      renewed = await renewMutation.mutateAsync();
    } catch {
      return;
    }
    onRenewed(renewed);
  }

  return (
    <section className={cn(panelVariants(), 'items-start')}>
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
