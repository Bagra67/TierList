import { useId, useRef, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router';

import { type Template, useCreateTemplate } from '../api/templates';
import { templateEditorPath } from '../constants/routes';
import { TEMPLATE_NAME_MAX_LENGTH } from '../constants/templates';
import { getFieldErrors, translateError, translateFieldError } from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { TextField } from './TextField';
import { Button } from './ui/button';

// <dialog> natif ouvert avec showModal() : le navigateur piège le focus dedans et le ferme avec Échap
export function CreateTemplateDialog() {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const titleId = useId();
  const createMutation = useCreateTemplate();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const fieldErrors = getFieldErrors(createMutation.error);

  function handleClose() {
    formRef.current?.reset();
    createMutation.reset();
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = String(new FormData(event.currentTarget).get('name'));
    let template: Template;
    try {
      template = await createMutation.mutateAsync({ name });
    } catch {
      return; // l'erreur est affichée depuis createMutation.error
    }
    dialogRef.current?.close();
    await navigate(templateEditorPath(template.id));
  }

  return (
    <>
      <Button type="button" onClick={() => dialogRef.current?.showModal()}>
        {t('templates.create.open')}
      </Button>
      <dialog
        ref={dialogRef}
        aria-labelledby={titleId}
        onClose={handleClose}
        className="m-auto w-full max-w-md rounded-xl bg-card p-6 text-sm text-card-foreground shadow-lg ring-1 ring-foreground/10 backdrop:bg-black/50"
      >
        <h2 id={titleId} className="text-lg font-semibold">
          {t('templates.create.title')}
        </h2>
        <form ref={formRef} onSubmit={handleSubmit} className="mt-4 flex flex-col gap-4">
          <TextField
            label={t('templates.create.name')}
            name="name"
            required
            maxLength={TEMPLATE_NAME_MAX_LENGTH}
            error={translateFieldError(t, fieldErrors.name)}
          />
          {createMutation.isError && (
            <ErrorMessage>{translateError(t, createMutation.error)}</ErrorMessage>
          )}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => dialogRef.current?.close()}>
              {t('templates.create.cancel')}
            </Button>
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending
                ? t('templates.create.submitting')
                : t('templates.create.submit')}
            </Button>
          </div>
        </form>
      </dialog>
    </>
  );
}
