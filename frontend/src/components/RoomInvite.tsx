import { useId, useState } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { Room } from '../api/rooms';
import { ErrorMessage } from './ErrorMessage';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';

// Résultat de la dernière copie du lien : rien tant qu'on n'a pas cliqué
type CopyStatus = 'idle' | 'copied' | 'failed';

interface RoomInviteProps {
  room: Room;
}

// Code et lien de la salle à partager (US-2.3) : le lien convient à un message, le code à une
// lecture à voix haute
export function RoomInvite({ room }: RoomInviteProps) {
  const linkId: string = useId();
  const [copyStatus, setCopyStatus] = useState<CopyStatus>('idle');
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();

  async function copyLink() {
    try {
      // navigator.clipboard n'existe que sur une page sécurisée (HTTPS ou localhost)
      await navigator.clipboard.writeText(room.link);
      setCopyStatus('copied');
    } catch {
      setCopyStatus('failed');
    }
  }

  return (
    <section className="flex w-full flex-col gap-4 rounded-xl border p-4">
      <div className="flex flex-col gap-1">
        <h2 className="text-sm text-muted-foreground">{t('rooms.lobby.code')}</h2>
        <p className="font-mono text-3xl font-semibold tracking-widest">{room.code}</p>
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor={linkId}>{t('rooms.lobby.link')}</Label>
        <div className="flex flex-wrap gap-2">
          <Input
            id={linkId}
            value={room.link}
            readOnly
            className="flex-1"
            onFocus={(event) => event.currentTarget.select()}
          />
          <Button type="button" variant="outline" onClick={copyLink}>
            {t('rooms.lobby.copyLink')}
          </Button>
        </div>
        {/* Annonce la copie aux lecteurs d'écran sans déplacer le focus */}
        <p aria-live="polite" className="text-sm text-muted-foreground">
          {copyStatus === 'copied' ? t('rooms.lobby.linkCopied') : ''}
        </p>
        {copyStatus === 'failed' && <ErrorMessage>{t('rooms.lobby.copyFailed')}</ErrorMessage>}
      </div>
    </section>
  );
}
