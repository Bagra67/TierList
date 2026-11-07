import { type FormEvent, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { type ReportReason, type ReportTargetKind, useCreateReport } from '../api/reports';
import { REPORT_DETAILS_MAX_LENGTH } from '../constants/moderation';
import { ApiError, translateError } from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { DialogActions, ModalDialog } from './ModalDialog';
import { TextField } from './TextField';
import { Button } from './ui/button';

const REPORT_REASONS: readonly ReportReason[] = [
  'illegal',
  'sexual',
  'violence_or_hate',
  'harassment',
  'spam',
  'other',
];

const REPORT_ALREADY_OPEN_CODE: string = 'report_already_open';

interface ReportButtonProps {
  targetKind: ReportTargetKind;
  targetId: string;
  contentName: string;
}

export function ReportButton({ targetKind, targetId, contentName }: ReportButtonProps) {
  const { t } = useTranslation();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const reportMutation = useCreateReport();
  const [reason, setReason] = useState<ReportReason | null>(null);
  const [details, setDetails] = useState<string>('');

  const alreadySent: boolean =
    reportMutation.error instanceof ApiError &&
    reportMutation.error.code === REPORT_ALREADY_OPEN_CODE;
  const answered: boolean = reportMutation.isSuccess || alreadySent;
  const trimmedDetails: string = details.trim();
  const isComplete: boolean = reason !== null && (reason !== 'other' || trimmedDetails !== '');

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (reason === null) return;
    reportMutation.mutate({ targetKind, targetId, reason, details: trimmedDetails });
  }

  function handleClose() {
    reportMutation.reset();
    setReason(null);
    setDetails('');
  }

  return (
    <>
      <Button
        type="button"
        variant="outline"
        size="sm"
        aria-label={t('report.openLabel', { name: contentName })}
        onClick={() => dialogRef.current?.showModal()}
      >
        {t('report.open')}
      </Button>
      <ModalDialog
        dialogRef={dialogRef}
        title={t(`report.title.${targetKind}`)}
        description={t('report.anonymous')}
        onClose={handleClose}
      >
        {answered ? (
          <div className="mt-4 flex flex-col gap-4">
            <p role="status">
              {alreadySent ? translateError(t, reportMutation.error) : t('report.sent')}
            </p>
            <div className="flex justify-end">
              <Button type="button" onClick={() => dialogRef.current?.close()}>
                {t('report.close')}
              </Button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-4">
            <fieldset className="flex flex-col gap-2">
              <legend className="mb-2 font-medium">{t('report.reason')}</legend>
              {REPORT_REASONS.map((candidate: ReportReason) => (
                <label key={candidate} className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="reason"
                    value={candidate}
                    checked={reason === candidate}
                    onChange={() => setReason(candidate)}
                  />
                  {t(`report.reasons.${candidate}`)}
                </label>
              ))}
            </fieldset>
            <TextField
              label={reason === 'other' ? t('report.detailsRequired') : t('report.detailsOptional')}
              name="details"
              required={reason === 'other'}
              maxLength={REPORT_DETAILS_MAX_LENGTH}
              value={details}
              onChange={(event) => setDetails(event.target.value)}
            />
            {reportMutation.isError && (
              <ErrorMessage>{translateError(t, reportMutation.error)}</ErrorMessage>
            )}
            <DialogActions
              cancelLabel={t('report.cancel')}
              onCancel={() => dialogRef.current?.close()}
              submitLabel={reportMutation.isPending ? t('report.submitting') : t('report.submit')}
              submitDisabled={reportMutation.isPending || !isComplete}
            />
          </form>
        )}
      </ModalDialog>
    </>
  );
}
