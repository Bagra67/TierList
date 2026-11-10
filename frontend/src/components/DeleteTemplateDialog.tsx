import { useTranslation } from 'react-i18next';

import { type TemplateSummary, useDeleteTemplate } from '../api/templates';
import { ConfirmMutationDialog } from './ConfirmMutationDialog';

interface DeleteTemplateDialogProps {
  template: TemplateSummary;
}

export function DeleteTemplateDialog({ template }: DeleteTemplateDialogProps) {
  const deleteMutation = useDeleteTemplate();
  const { t } = useTranslation();

  return (
    <ConfirmMutationDialog
      openLabel={t('templates.delete.open')}
      openAriaLabel={t('templates.delete.openLabel', { name: template.name })}
      openVariant="outline"
      title={t('templates.delete.title', { name: template.name })}
      description={t('templates.delete.warning')}
      cancelLabel={t('templates.delete.cancel')}
      submitLabel={t('templates.delete.submit')}
      submittingLabel={t('templates.delete.submitting')}
      mutation={deleteMutation}
      confirm={() => deleteMutation.mutateAsync(template.id)}
    />
  );
}
