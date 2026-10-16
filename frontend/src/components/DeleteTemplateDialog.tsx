import { useId, useRef, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { type TemplateSummary, useDeleteTemplate } from '../api/templates';
import { translateError } from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { Button } from './ui/button';

interface DeleteTemplateDialogProps {
  template: TemplateSummary;
}

// Confirmation avant suppression, dans un <dialog> natif (focus piégé, fermeture avec Échap)
export function DeleteTemplateDialog({ template }: DeleteTemplateDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();
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
      <dialog
        ref={dialogRef}
        aria-labelledby={titleId}
        onClose={() => deleteMutation.reset()}
        className="m-auto w-full max-w-md rounded-xl bg-card p-6 text-sm text-card-foreground shadow-lg ring-1 ring-foreground/10 backdrop:bg-black/50"
      >
        <h2 id={titleId} className="text-lg font-semibold">
          {t('templates.delete.title', { name: template.name })}
        </h2>
        <p className="mt-2 text-muted-foreground">{t('templates.delete.warning')}</p>
        <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-4">
          {deleteMutation.isError && (
            <ErrorMessage>{translateError(t, deleteMutation.error)}</ErrorMessage>
          )}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => dialogRef.current?.close()}>
              {t('templates.delete.cancel')}
            </Button>
            <Button type="submit" variant="destructive" disabled={deleteMutation.isPending}>
              {deleteMutation.isPending
                ? t('templates.delete.submitting')
                : t('templates.delete.submit')}
            </Button>
          </div>
        </form>
      </dialog>
    </>
  );
}
