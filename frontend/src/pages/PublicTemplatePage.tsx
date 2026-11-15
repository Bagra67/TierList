import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router';

import { type PublicTemplate, type PublicTile, usePublicTemplate } from '../api/marketplace';
import { CenteredCardPage } from '../components/CenteredCardPage';
import { EmptyState } from '../components/EmptyState';
import { ErrorMessage } from '../components/ErrorMessage';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { PageContainer } from '../components/PageContainer';
import { ReportButton } from '../components/ReportButton';
import { TemplateTagList } from '../components/TemplateTagList';
import { TemplateTierChips } from '../components/TemplateTierChips';
import { TemplateTileCard } from '../components/TemplateTileCard';
import { Button } from '../components/ui/button';
import { ROUTES } from '../constants/routes';
import { isTemplateId } from '../constants/templates';
import { ApiError, translateError } from '../errors/apiError';

const TEMPLATE_NOT_FOUND_CODE: string = 'template_not_found';

function isUnavailable(error: Error): boolean {
  return error instanceof ApiError && error.code === TEMPLATE_NOT_FOUND_CODE;
}

export function PublicTemplatePage() {
  const { t } = useTranslation();
  const { templateId = '' } = useParams();
  const { data: template, error } = usePublicTemplate(templateId);

  if (!isTemplateId(templateId) || (error !== null && isUnavailable(error))) {
    return <UnavailableTemplate />;
  }

  return (
    <PageContainer width="app" className="flex flex-col items-start gap-6">
      {template !== undefined ? (
        <TemplateContent template={template} />
      ) : error !== null ? (
        <ErrorMessage>{translateError(t, error)}</ErrorMessage>
      ) : (
        <LoadingSkeleton shape="board" />
      )}
    </PageContainer>
  );
}

function UnavailableTemplate() {
  const { t } = useTranslation();
  return (
    <CenteredCardPage title={t('publicTemplate.unavailable.title')}>
      <p>{t('publicTemplate.unavailable.message')}</p>
      <Button asChild className="w-full">
        <Link to={ROUTES.HOME}>{t('notFound.backHome')}</Link>
      </Button>
    </CenteredCardPage>
  );
}

function TemplateContent({ template }: { template: PublicTemplate }) {
  const { t } = useTranslation();
  return (
    <>
      <div className="flex w-full flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 flex-col gap-2">
          <h1 className="text-2xl font-semibold break-words">{template.name}</h1>
          <p className="text-muted-foreground">
            {t('publicTemplate.byOwner', { owner: template.owner_name })}
          </p>
          <TemplateTagList tags={template.tags} />
        </div>
        <ReportButton targetKind="template" targetId={template.id} contentName={template.name} />
      </div>

      <section className="flex w-full flex-col items-start gap-3">
        <h2 className="text-lg font-semibold">{t('publicTemplate.tiers')}</h2>
        <TemplateTierChips tiers={template.tiers} />
      </section>

      <section className="flex w-full flex-col items-start gap-3">
        <h2 className="text-lg font-semibold">
          {t('publicTemplate.items', { count: template.tiles.length })}
        </h2>
        {template.tiles.length === 0 ? (
          <EmptyState message={t('publicTemplate.noItems')} />
        ) : (
          <ul className="grid w-full grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
            {template.tiles.map((tile: PublicTile, index: number) => (
              <TemplateTileCard
                key={tile.id}
                imageUrl={tile.image_url}
                imageRemoved={tile.image_removed}
                imageAlt={t('publicTemplate.itemImage', { number: index + 1 })}
                text={tile.text}
              />
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
