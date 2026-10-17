import { type FormEvent, useRef } from 'react';
import { useTranslation } from 'react-i18next';

import { useEndCooldown } from '../api/rooms';
import { translateError } from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { DialogActions, ModalDialog } from './ModalDialog';
import { Button } from './ui/button';

interface EndCooldownDialogProps {
  code: string;
}

// « Terminer maintenant » (US-4.1), réservé au room admin : les classements de tous deviennent
// définitifs, d'où la confirmation dans un <dialog> natif (focus piégé, fermeture avec Échap)
export function EndCooldownDialog({ code }: EndCooldownDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const endMutation = useEndCooldown(code);
  const { t } = useTranslation();

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await endMutation.mutateAsync();
    } catch {
      return; // l'erreur est affichée depuis endMutation.error
    }
    // La salle renvoyée n'a plus de partie : l'écran du cooldown et ce dialogue disparaissent
    dialogRef.current?.close();
  }

  return (
    <>
      <Button type="button" variant="destructive" onClick={() => dialogRef.current?.showModal()}>
        {t('rooms.game.cooldown.end.open')}
      </Button>
      <ModalDialog
        dialogRef={dialogRef}
        title={t('rooms.game.cooldown.end.title')}
        description={t('rooms.game.cooldown.end.warning')}
        onClose={() => endMutation.reset()}
      >
        <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-4">
          {endMutation.isError && (
            <ErrorMessage>{translateError(t, endMutation.error)}</ErrorMessage>
          )}
          <DialogActions
            cancelLabel={t('rooms.game.cooldown.end.cancel')}
            onCancel={() => dialogRef.current?.close()}
            submitLabel={
              endMutation.isPending
                ? t('rooms.game.cooldown.end.submitting')
                : t('rooms.game.cooldown.end.submit')
            }
            submitVariant="destructive"
            submitDisabled={endMutation.isPending}
          />
        </form>
      </ModalDialog>
    </>
  );
}
