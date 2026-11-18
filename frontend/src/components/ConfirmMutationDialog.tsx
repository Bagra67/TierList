import { type ComponentProps, type FormEvent, type ReactNode, useRef } from 'react';
import { useTranslation } from 'react-i18next';

import { translateError } from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { DialogActions, ModalDialog } from './ModalDialog';
import { Button } from './ui/button';

interface ConfirmationMutation {
  isPending: boolean;
  isError: boolean;
  error: Error | null;
  reset: () => void;
}

interface ConfirmMutationDialogProps {
  openLabel: string;
  openAriaLabel?: string;
  openVariant: ComponentProps<typeof Button>['variant'];
  openSize?: ComponentProps<typeof Button>['size'];
  title: string;
  description: string;
  cancelLabel: string;
  submitLabel: string;
  submittingLabel: string;
  mutation: ConfirmationMutation;
  confirm: () => Promise<unknown>;
  onConfirmed?: () => void;
  onClose?: () => void;
  children?: ReactNode;
}

export function ConfirmMutationDialog({
  openLabel,
  openAriaLabel,
  openVariant,
  openSize,
  title,
  description,
  cancelLabel,
  submitLabel,
  submittingLabel,
  mutation,
  confirm,
  onConfirmed,
  onClose,
  children,
}: ConfirmMutationDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const { t } = useTranslation();

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await confirm();
    } catch {
      return;
    }
    dialogRef.current?.close();
    onConfirmed?.();
  }

  function handleClose() {
    mutation.reset();
    onClose?.();
  }

  return (
    <>
      <Button
        type="button"
        variant={openVariant}
        size={openSize}
        aria-label={openAriaLabel}
        onClick={() => dialogRef.current?.showModal()}
      >
        {openLabel}
      </Button>
      <ModalDialog
        dialogRef={dialogRef}
        title={title}
        description={description}
        onClose={handleClose}
      >
        <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-4">
          {children}
          {mutation.isError && <ErrorMessage>{translateError(t, mutation.error)}</ErrorMessage>}
          <DialogActions
            cancelLabel={cancelLabel}
            onCancel={() => dialogRef.current?.close()}
            submitLabel={mutation.isPending ? submittingLabel : submitLabel}
            submitVariant="destructive"
            submitDisabled={mutation.isPending}
          />
        </form>
      </ModalDialog>
    </>
  );
}
