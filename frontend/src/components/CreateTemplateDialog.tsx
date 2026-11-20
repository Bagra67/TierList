import type { UseMutationResult } from '@tanstack/react-query';
import { useRef, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router';

import { useCreateOfficialTemplate } from '../api/officialTemplates';
import { type Template, useCreateTemplate } from '../api/templates';
import { officialTemplateEditorPath, templateEditorPath } from '../constants/routes';
import { TEMPLATE_NAME_MAX_LENGTH } from '../constants/templates';
import { getFieldErrors, translateError, translateFieldError } from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { TextField } from './TextField';
import { DialogActions, ModalDialog } from './ModalDialog';
import { Button } from './ui/button';

export function CreateTemplateDialog() {
  const { t } = useTranslation();
  return (
    <CreateTemplateDialogView
      createMutation={useCreateTemplate()}
      editorPath={templateEditorPath}
      openLabel={t('templates.create.open')}
      title={t('templates.create.title')}
    />
  );
}

export function CreateOfficialTemplateDialog() {
  const { t } = useTranslation();
  return (
    <CreateTemplateDialogView
      createMutation={useCreateOfficialTemplate()}
      editorPath={officialTemplateEditorPath}
      openLabel={t('officialTemplates.create.open')}
      title={t('officialTemplates.create.title')}
    />
  );
}

interface CreateTemplateDialogViewProps {
  createMutation: UseMutationResult<Template, Error, { name: string }>;
  editorPath: (templateId: string) => string;
  openLabel: string;
  title: string;
}

function CreateTemplateDialogView({
  createMutation,
  editorPath,
  openLabel,
  title,
}: CreateTemplateDialogViewProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const formRef = useRef<HTMLFormElement>(null);
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
      return;
    }
    if (dialogRef.current?.open !== true) return;
    dialogRef.current.close();
    await navigate(editorPath(template.id));
  }

  return (
    <>
      <Button type="button" onClick={() => dialogRef.current?.showModal()}>
        {openLabel}
      </Button>
      <ModalDialog dialogRef={dialogRef} title={title} onClose={handleClose}>
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
          <DialogActions
            cancelLabel={t('templates.create.cancel')}
            onCancel={() => dialogRef.current?.close()}
            submitLabel={
              createMutation.isPending
                ? t('templates.create.submitting')
                : t('templates.create.submit')
            }
            submitDisabled={createMutation.isPending}
          />
        </form>
      </ModalDialog>
    </>
  );
}
