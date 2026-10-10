import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import { type Template, type TemplateChange, useRenameTemplate } from '../api/templates';
import { TEMPLATE_NAME_MAX_LENGTH } from '../constants/templates';
import {
  type FieldError,
  getFieldErrors,
  translateError,
  translateFieldError,
} from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { InlineEditField } from './InlineEditField';

interface TemplateNameFieldProps {
  template: Template;
}

// Nom du template, enregistré dès qu'il est validé ou que le champ est quitté
export function TemplateNameField({ template }: TemplateNameFieldProps) {
  const renameMutation: TemplateChange<string> = useRenameTemplate(template.id);
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const nameError: FieldError | undefined = getFieldErrors(renameMutation.error).name;

  return (
    <div className="flex w-full flex-col gap-1">
      <InlineEditField
        key={template.name}
        label={t('templates.editor.name')}
        value={template.name}
        maxLength={TEMPLATE_NAME_MAX_LENGTH}
        error={translateFieldError(t, nameError)}
        onSave={(name) => renameMutation.mutate(name)}
      />
      {renameMutation.isError && nameError === undefined && (
        <ErrorMessage>{translateError(t, renameMutation.error)}</ErrorMessage>
      )}
    </div>
  );
}
