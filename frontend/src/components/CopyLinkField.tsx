import { useId, useState } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import { ErrorMessage } from './ErrorMessage';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';

// Résultat de la dernière copie du lien : rien tant qu'on n'a pas cliqué
type CopyStatus = 'idle' | 'copied' | 'failed';

interface CopyLinkFieldProps {
  label: string;
  link: string;
}

// Lien en lecture seule avec un bouton « Copier le lien » : la copie est annoncée aux lecteurs
// d'écran, ou un message demande de copier à la main si le presse-papiers refuse
export function CopyLinkField({ label, link }: CopyLinkFieldProps) {
  const linkId: string = useId();
  const [copyStatus, setCopyStatus] = useState<CopyStatus>('idle');
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();

  async function copyLink() {
    try {
      // navigator.clipboard n'existe que sur une page sécurisée (HTTPS ou localhost)
      await navigator.clipboard.writeText(link);
      setCopyStatus('copied');
    } catch {
      setCopyStatus('failed');
    }
  }

  return (
    <div className="flex w-full flex-col gap-2">
      <Label htmlFor={linkId}>{label}</Label>
      <div className="flex flex-wrap gap-2">
        <Input
          id={linkId}
          value={link}
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
  );
}
