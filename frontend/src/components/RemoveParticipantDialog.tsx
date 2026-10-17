import { type FormEvent, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { type Participant, useRemoveParticipant } from '../api/rooms';
import { translateError } from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { DialogActions, ModalDialog } from './ModalDialog';
import { Button } from './ui/button';

interface RemoveParticipantDialogProps {
  code: string;
  participant: Participant;
}

// Confirmation avant de retirer un participant (US-2.11), ou de le bannir (US-2.12), dans un
// <dialog> natif (focus piégé, fermeture avec Échap). Réservé au room admin.
export function RemoveParticipantDialog({ code, participant }: RemoveParticipantDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const removeMutation = useRemoveParticipant(code);
  const [ban, setBan] = useState<boolean>(false);
  const { t } = useTranslation();
  const name: string = participant.display_name;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await removeMutation.mutateAsync({ participantId: participant.id, ban });
    } catch {
      return; // l'erreur est affichée depuis removeMutation.error
    }
    // La salle renvoyée ne contient plus ce participant : la ligne et son dialogue disparaissent
    dialogRef.current?.close();
  }

  function handleClose() {
    removeMutation.reset();
    setBan(false);
  }

  return (
    <>
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="ml-auto"
        aria-label={t('rooms.lobby.remove.openLabel', { name })}
        onClick={() => dialogRef.current?.showModal()}
      >
        {t('rooms.lobby.remove.open')}
      </Button>
      <ModalDialog
        dialogRef={dialogRef}
        title={t('rooms.lobby.remove.title', { name })}
        description={t('rooms.lobby.remove.warning')}
        onClose={handleClose}
      >
        <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-4">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={ban}
              onChange={(event) => setBan(event.target.checked)}
            />
            {t('rooms.lobby.remove.ban')}
          </label>
          {/* Un invité n'a pas de compte : seul son navigateur est reconnu (US-2.12) */}
          {ban && participant.is_guest && (
            <p className="text-muted-foreground">{t('rooms.lobby.remove.guestWarning')}</p>
          )}
          {removeMutation.isError && (
            <ErrorMessage>{translateError(t, removeMutation.error)}</ErrorMessage>
          )}
          <DialogActions
            cancelLabel={t('rooms.lobby.remove.cancel')}
            onCancel={() => dialogRef.current?.close()}
            submitLabel={
              removeMutation.isPending
                ? t('rooms.lobby.remove.submitting')
                : ban
                  ? t('rooms.lobby.remove.submitBan')
                  : t('rooms.lobby.remove.submit')
            }
            submitVariant="destructive"
            submitDisabled={removeMutation.isPending}
          />
        </form>
      </ModalDialog>
    </>
  );
}
