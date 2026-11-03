import { type ReactNode, type RefObject, useId } from 'react';

import { Button } from './ui/button';

interface ModalDialogProps {
  dialogRef: RefObject<HTMLDialogElement | null>;
  title: string;
  description?: string;
  onClose?: () => void;
  children: ReactNode;
}

export function ModalDialog({
  dialogRef,
  title,
  description,
  onClose,
  children,
}: ModalDialogProps) {
  const titleId: string = useId();
  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={titleId}
      onClose={onClose}
      className="m-auto w-full max-w-md rounded-xl bg-card p-6 text-sm text-card-foreground shadow-lg ring-1 ring-foreground/10 backdrop:bg-black/50"
    >
      <h2 id={titleId} className="text-lg font-semibold">
        {title}
      </h2>
      {description !== undefined && <p className="mt-2 text-muted-foreground">{description}</p>}
      {children}
    </dialog>
  );
}

interface DialogActionsProps {
  cancelLabel: string;
  onCancel: () => void;
  submitLabel: string;
  submitVariant?: 'default' | 'destructive';
  submitDisabled: boolean;
}

export function DialogActions({
  cancelLabel,
  onCancel,
  submitLabel,
  submitVariant = 'default',
  submitDisabled,
}: DialogActionsProps) {
  return (
    <div className="flex justify-end gap-2">
      <Button type="button" variant="outline" onClick={onCancel}>
        {cancelLabel}
      </Button>
      <Button type="submit" variant={submitVariant} disabled={submitDisabled}>
        {submitLabel}
      </Button>
    </div>
  );
}
