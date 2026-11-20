import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import { cn } from 'cn';

import { type OfficialTemplateSummary, useOfficialTemplates } from '../api/officialTemplates';
import { CreateTemplateDialog } from '../components/CreateTemplateDialog';
import { EmptyState } from '../components/EmptyState';
import { ErrorMessage } from '../components/ErrorMessage';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { OfficialTemplateStateBadge } from '../components/OfficialTemplateStateBadge';
import { TemplateFeaturedBadge } from '../components/TemplateFeaturedBadge';
import { panelVariants } from '../components/ui/panel';
import { textLinkClassName } from '../components/ui/text-link';
import { useDocumentTitle } from '../components/useDocumentTitle';
import { officialTemplateEditorPath } from '../constants/routes';
import { translateError } from '../errors/apiError';

export function ModerationOfficialTemplatesPage() {
  const { t } = useTranslation();
  useDocumentTitle(t('officialTemplates.title'));
  const query = useOfficialTemplates();

  return (
    <div className="flex flex-col items-start gap-6">
      <div className="flex w-full flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-2">
          <h1 className="text-2xl font-semibold">{t('officialTemplates.title')}</h1>
          <p className="max-w-prose text-muted-foreground">{t('officialTemplates.intro')}</p>
        </div>
        <CreateTemplateDialog official />
      </div>

      {query.isPending && <LoadingSkeleton shape="list" />}
      {query.isError && <ErrorMessage>{translateError(t, query.error)}</ErrorMessage>}
      {query.data?.length === 0 && <EmptyState message={t('officialTemplates.empty')} />}
      {query.data !== undefined && query.data.length > 0 && (
        <ul className={panelVariants({ variant: 'list', className: 'w-full' })}>
          {query.data.map((template: OfficialTemplateSummary) => (
            <OfficialTemplateRow key={template.id} template={template} />
          ))}
        </ul>
      )}
    </div>
  );
}

function OfficialTemplateRow({ template }: { template: OfficialTemplateSummary }) {
  const { t } = useTranslation();
  return (
    <li className="flex flex-col gap-1 px-4 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <Link
          to={officialTemplateEditorPath(template.id)}
          className={cn(textLinkClassName, 'font-medium break-words')}
        >
          {template.name}
        </Link>
        <OfficialTemplateStateBadge visibility={template.visibility} />
        {template.featured && <TemplateFeaturedBadge />}
      </div>
      <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
        <span>{t('officialTemplates.tileCount', { count: template.tile_count })}</span>
        <time dateTime={template.updated_at}>
          {t('officialTemplates.updatedAt', { date: new Date(template.updated_at) })}
        </time>
        {template.editing_by_name !== null && (
          <span className="inline-flex items-center gap-1.5">
            <span aria-hidden="true" className="size-2 rounded-full bg-success" />
            {t('officialTemplates.editing', { editor: template.editing_by_name })}
          </span>
        )}
      </p>
    </li>
  );
}
