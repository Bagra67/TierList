import { useRef, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { type TemplateSummary, useDeleteTemplate } from '../api/templates';
import { translateError } from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { DialogActions, ModalDialog } from './ModalDialog';
import { Button } from './ui/button';

interface DeleteTemplateDialogProps {
  template: TemplateSummary;
}

// Confirmation avant suppression, dans un <dialog> natif (focus piégé, fermeture avec Échap)
export function DeleteTemplateDialog({ template }: DeleteTemplateDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const deleteMutation = useDeleteTemplate();
  const { t } = useTranslation();

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await deleteMutation.mutateAsync(template.id);
    } catch {
      return; // l'erreur est affichée depuis deleteMutation.error
    }
    // La liste rafraîchie ne contient plus ce template : la ligne et son dialogue disparaissent
    dialogRef.current?.close();
  }

  return (
    <>
      <Button
        type="button"
        variant="outline"
        aria-label={t('templates.delete.openLabel', { name: template.name })}
        onClick={() => dialogRef.current?.showModal()}
      >
        {t('templates.delete.open')}
      </Button>
      <ModalDialog
        dialogRef={dialogRef}
        title={t('templates.delete.title', { name: template.name })}
        description={t('templates.delete.warning')}
        onClose={() => deleteMutation.reset()}
      >
        <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-4">
          {deleteMutation.isError && (
            <ErrorMessage>{translateError(t, deleteMutation.error)}</ErrorMessage>
          )}
          <DialogActions
            cancelLabel={t('templates.delete.cancel')}
            onCancel={() => dialogRef.current?.close()}
            submitLabel={
              deleteMutation.isPending
                ? t('templates.delete.submitting')
                : t('templates.delete.submit')
            }
            submitVariant="destructive"
            submitDisabled={deleteMutation.isPending}
          />
        </form>
      </ModalDialog>
    </>
  );
}
