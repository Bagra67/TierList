import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { type RefObject, createRef } from 'react';
import { describe, expect, it, type Mock, vi } from 'vitest';

import { ModerationReasonDialog } from './ModerationReasonDialog';

function renderDialog(
  props: Partial<{
    isPending: boolean;
    error: string | null;
    onSubmit: (reason: string) => Promise<boolean>;
  }> = {},
): RefObject<HTMLDialogElement | null> {
  const dialogRef: RefObject<HTMLDialogElement | null> = createRef<HTMLDialogElement>();
  render(
    <ModerationReasonDialog
      dialogRef={dialogRef}
      title="Supprimer cette image"
      description="Définitif."
      submitLabel="Supprimer"
      submittingLabel="Suppression…"
      destructive
      isPending={props.isPending ?? false}
      translatedFailureMessage={props.error ?? null}
      onSubmit={props.onSubmit ?? (() => Promise.resolve(true))}
      onClose={() => {}}
    />,
  );
  dialogRef.current?.showModal();
  return dialogRef;
}

describe('ModerationReasonDialog', () => {
  it('needs a reason that is not only spaces', () => {
    renderDialog();
    const submit = screen.getByRole('button', { name: 'Supprimer' });

    expect(submit).toBeDisabled();
    fireEvent.change(screen.getByLabelText('Motif'), { target: { value: '   ' } });
    expect(submit).toBeDisabled();
    expect(screen.getByLabelText('Motif')).toHaveAttribute('maxlength', '500');
  });

  it('sends the trimmed reason and closes once the action succeeded', async () => {
    const onSubmit: Mock<(reason: string) => Promise<boolean>> = vi.fn(() => Promise.resolve(true));
    const dialogRef = renderDialog({ onSubmit });
    const close: Mock<() => void> = vi.fn();
    (dialogRef.current as HTMLDialogElement).close = close;

    fireEvent.change(screen.getByLabelText('Motif'), { target: { value: ' Spam ' } });
    fireEvent.click(screen.getByRole('button', { name: 'Supprimer' }));

    await waitFor(() => expect(close).toHaveBeenCalledOnce());
    expect(onSubmit).toHaveBeenCalledWith('Spam');
  });

  it('stays open and shows the error when the action failed', async () => {
    const dialogRef = renderDialog({
      onSubmit: () => Promise.resolve(false),
      error: 'Cette image est introuvable.',
    });
    const close: Mock<() => void> = vi.fn();
    (dialogRef.current as HTMLDialogElement).close = close;

    fireEvent.change(screen.getByLabelText('Motif'), { target: { value: 'Spam' } });
    fireEvent.click(screen.getByRole('button', { name: 'Supprimer' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Cette image est introuvable.');
    expect(close).not.toHaveBeenCalled();
  });

  it('cannot be sent twice while the action is running', () => {
    renderDialog({ isPending: true });

    fireEvent.change(screen.getByLabelText('Motif'), { target: { value: 'Spam' } });

    expect(screen.getByRole('button', { name: 'Suppression…' })).toBeDisabled();
  });
});
