import { useId } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router';

import {
  type OfficialTemplateChange,
  useChangeOfficialTemplate,
  useDeleteOfficialTemplate,
} from '../api/officialTemplates';
import type { Template } from '../api/templates';
import { ROUTES } from '../constants/routes';
import { translateError } from '../errors/apiError';
import { ConfirmMutationDialog } from './ConfirmMutationDialog';
import { ErrorMessage } from './ErrorMessage';
import { OfficialTemplateStateBadge } from './OfficialTemplateStateBadge';
import { Button } from './ui/button';
import { panelVariants } from './ui/panel';

export function OfficialTemplateStatusField({ template }: { template: Template }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const featureHelpId: string = useId();
  const changeMutation = useChangeOfficialTemplate(template.id);
  const deleteMutation = useDeleteOfficialTemplate(template.id);
  const published: boolean = template.visibility === 'public';

  function change(kind: OfficialTemplateChange) {
    changeMutation.mutate(kind);
  }

  return (
    <section
      aria-labelledby={`${featureHelpId}-title`}
      className={panelVariants({ className: 'flex min-w-0 flex-col gap-3 p-4' })}
    >
      <h2 id={`${featureHelpId}-title`} className="text-sm font-semibold">
        {t('officialTemplates.status.title')}
      </h2>
      <p className="flex flex-wrap items-center gap-2 text-sm">
        <OfficialTemplateStateBadge visibility={template.visibility} />
        {published
          ? t('officialTemplates.status.publishedDescription')
          : t('officialTemplates.status.draftDescription')}
      </p>
      <div>
        {published ? (
          <Button
            type="button"
            variant="outline"
            disabled={changeMutation.isPending}
            onClick={() => change('unpublish')}
          >
            {t('officialTemplates.status.unpublish')}
          </Button>
        ) : (
          <Button
            type="button"
            disabled={changeMutation.isPending || template.tiles.length === 0}
            onClick={() => change('publish')}
          >
            {t('officialTemplates.status.publish')}
          </Button>
        )}
      </div>
      <label className="flex items-start gap-2 text-sm has-disabled:text-muted-foreground">
        <input
          type="checkbox"
          checked={template.featured}
          disabled={!published || changeMutation.isPending}
          aria-describedby={featureHelpId}
          onChange={(event) => change(event.target.checked ? 'feature' : 'unfeature')}
          className="mt-0.5 size-4 shrink-0 accent-foreground"
        />
        <span className="flex flex-col gap-0.5">
          {t('officialTemplates.status.feature')}
          <span id={featureHelpId} className="text-muted-foreground">
            {published
              ? t('officialTemplates.status.featureHelp')
              : t('officialTemplates.status.featureNeedsPublishing')}
          </span>
        </span>
      </label>
      {changeMutation.isError && (
        <ErrorMessage>{translateError(t, changeMutation.error)}</ErrorMessage>
      )}
      <div className="border-t border-border pt-3">
        <ConfirmMutationDialog
          openLabel={t('officialTemplates.delete.open')}
          openVariant="outline"
          openSize="sm"
          title={t('officialTemplates.delete.title', { name: template.name })}
          description={t('officialTemplates.delete.warning')}
          cancelLabel={t('officialTemplates.delete.cancel')}
          submitLabel={t('officialTemplates.delete.submit')}
          submittingLabel={t('officialTemplates.delete.submitting')}
          mutation={deleteMutation}
          confirm={() => deleteMutation.mutateAsync()}
          onConfirmed={() => void navigate(ROUTES.MODERATION_OFFICIAL_TEMPLATES)}
        />
      </div>
    </section>
  );
}
