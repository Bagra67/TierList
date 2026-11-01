import { type FormEvent, type RefObject, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { MODERATION_REASON_MAX_LENGTH } from '../constants/moderation';
import { ErrorMessage } from './ErrorMessage';
import { DialogActions, ModalDialog } from './ModalDialog';
import { TextField } from './TextField';

interface ModerationReasonDialogProps {
  // Ouvert par le parent avec dialogRef.current.showModal()
  dialogRef: RefObject<HTMLDialogElement | null>;
  title: string;
  // Ce que fait l'action, et si elle peut être annulée
  description: string;
  submitLabel: string;
  submittingLabel: string;
  // Action définitive (suppression) : bouton rouge
  destructive: boolean;
  isPending: boolean;
  // Message déjà traduit de l'échec de la dernière tentative
  error: string | null;
  // Lance l'action avec le motif ; résolue si elle a réussi (le dialogue se ferme alors)
  onSubmit: (reason: string) => Promise<boolean>;
  onClose: () => void;
}

// Motif d'une décision de modération (US-1.9), écrit au journal : demandé avant de masquer,
// réafficher ou supprimer un contenu. Le même dialogue sert à toutes les pages de modération.
export function ModerationReasonDialog({
  dialogRef,
  title,
  description,
  submitLabel,
  submittingLabel,
  destructive,
  isPending,
  error,
  onSubmit,
  onClose,
}: ModerationReasonDialogProps) {
  const { t } = useTranslation();
  const [reason, setReason] = useState<string>('');

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (await onSubmit(reason.trim())) dialogRef.current?.close();
  }

  function handleClose() {
    setReason('');
    onClose();
  }

  return (
    <ModalDialog
      dialogRef={dialogRef}
      title={title}
      description={description}
      onClose={handleClose}
    >
      <form onSubmit={(event) => void handleSubmit(event)} className="mt-4 flex flex-col gap-4">
        <TextField
          label={t('moderation.reasonDialog.reason')}
          name="reason"
          required
          maxLength={MODERATION_REASON_MAX_LENGTH}
          value={reason}
          onChange={(event) => setReason(event.target.value)}
        />
        {error !== null && <ErrorMessage>{error}</ErrorMessage>}
        <DialogActions
          cancelLabel={t('moderation.reasonDialog.cancel')}
          onCancel={() => dialogRef.current?.close()}
          submitLabel={isPending ? submittingLabel : submitLabel}
          submitVariant={destructive ? 'destructive' : 'default'}
          // Un motif fait seulement d'espaces serait refusé par le backend
          submitDisabled={isPending || reason.trim() === ''}
        />
      </form>
    </ModalDialog>
  );
}
