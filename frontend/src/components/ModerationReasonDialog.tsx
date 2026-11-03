import { type FormEvent, type RefObject, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { MODERATION_REASON_MAX_LENGTH } from '../constants/moderation';
import { ErrorMessage } from './ErrorMessage';
import { DialogActions, ModalDialog } from './ModalDialog';
import { TextField } from './TextField';

interface ModerationReasonDialogProps {
  dialogRef: RefObject<HTMLDialogElement | null>;
  title: string;
  description: string;
  submitLabel: string;
  submittingLabel: string;
  destructive: boolean;
  isPending: boolean;
  // Message déjà traduit de l'échec de la dernière tentative
  error: string | null;
  onSubmit: (reason: string) => Promise<boolean>;
  onClose: () => void;
}

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
          submitDisabled={isPending || reason.trim() === ''}
        />
      </form>
    </ModalDialog>
  );
}
