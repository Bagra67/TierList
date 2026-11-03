import { type FormEvent, type RefObject, useId, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { useBanAccount } from '../api/moderation';
import { MODERATION_REASON_MAX_LENGTH } from '../constants/moderation';
import { translateError } from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { startOfNextDay, today } from './localDays';
import { DialogActions, ModalDialog } from './ModalDialog';
import { TextField } from './TextField';
import { Input } from './ui/input';
import { Label } from './ui/label';

type BanDuration = 'temporary' | 'permanent';

interface BanAccountDialogProps {
  dialogRef: RefObject<HTMLDialogElement | null>;
  accountId: string;
  displayName: string;
}

export function BanAccountDialog({ dialogRef, accountId, displayName }: BanAccountDialogProps) {
  const { t } = useTranslation();
  const untilId: string = useId();
  const banMutation = useBanAccount();
  const [duration, setDuration] = useState<BanDuration>('temporary');
  const [until, setUntil] = useState<string>('');
  const [reason, setReason] = useState<string>('');

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await banMutation.mutateAsync({
        accountId,
        reason: reason.trim(),
        endsAt: duration === 'temporary' ? startOfNextDay(until) : undefined,
      });
    } catch {
      return;
    }
    dialogRef.current?.close();
  }

  function handleClose() {
    banMutation.reset();
    setDuration('temporary');
    setUntil('');
    setReason('');
  }

  const isComplete: boolean = reason.trim() !== '' && (duration === 'permanent' || until !== '');

  return (
    <ModalDialog
      dialogRef={dialogRef}
      title={t('moderation.ban.title', { name: displayName })}
      description={t('moderation.ban.hint')}
      onClose={handleClose}
    >
      <form onSubmit={(event) => void handleSubmit(event)} className="mt-4 flex flex-col gap-4">
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-2 font-medium">{t('moderation.ban.duration')}</legend>
          <label className="flex items-center gap-2">
            <input
              type="radio"
              name="duration"
              value="temporary"
              checked={duration === 'temporary'}
              onChange={() => setDuration('temporary')}
            />
            {t('moderation.ban.temporary')}
          </label>
          {duration === 'temporary' && (
            <div className="ml-6 flex flex-col gap-2">
              <Label htmlFor={untilId}>{t('moderation.ban.until')}</Label>
              <Input
                id={untilId}
                type="date"
                required
                min={today()}
                value={until}
                onChange={(event) => setUntil(event.target.value)}
              />
            </div>
          )}
          <label className="flex items-center gap-2">
            <input
              type="radio"
              name="duration"
              value="permanent"
              checked={duration === 'permanent'}
              onChange={() => setDuration('permanent')}
            />
            {t('moderation.ban.permanent')}
          </label>
        </fieldset>
        <TextField
          label={t('moderation.ban.reason')}
          name="reason"
          required
          maxLength={MODERATION_REASON_MAX_LENGTH}
          value={reason}
          onChange={(event) => setReason(event.target.value)}
        />
        {banMutation.isError && <ErrorMessage>{translateError(t, banMutation.error)}</ErrorMessage>}
        <DialogActions
          cancelLabel={t('moderation.reasonDialog.cancel')}
          onCancel={() => dialogRef.current?.close()}
          submitLabel={
            banMutation.isPending ? t('moderation.ban.submitting') : t('moderation.ban.submit')
          }
          submitVariant="destructive"
          submitDisabled={banMutation.isPending || !isComplete}
        />
      </form>
    </ModalDialog>
  );
}
