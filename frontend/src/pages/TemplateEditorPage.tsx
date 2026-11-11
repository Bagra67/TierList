import type { UseQueryResult } from '@tanstack/react-query';
import { useEffect } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';
import { Link, type Params, useParams } from 'react-router';
import { cn } from 'cn';

import { type Template, useTemplate } from '../api/templates';
import { CreateRoomButton } from '../components/CreateRoomButton';
import { TemplateHiddenNotice } from '../components/TemplateHiddenNotice';
import { ErrorMessage } from '../components/ErrorMessage';
import { TemplateNameField } from '../components/TemplateNameField';
import { TemplateVisibilityField } from '../components/TemplateVisibilityField';
import { TierEditor } from '../components/TierEditor';
import { TileEditor } from '../components/TileEditor';
import { textLinkClassName } from '../components/ui/text-link';
import {
  EDITOR_COLUMNS_FITTING_FULL_TIER_ROW_CLASS,
  FILL_HEIGHT_UNDER_HEADER_ON_LARGE_SCREEN_CLASS,
} from '../constants/layout';
import { ROUTES } from '../constants/routes';
import { isTemplateId } from '../constants/templates';
import { translateError } from '../errors/apiError';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { PageContainer } from '../components/PageContainer';
import { NotFoundPage } from './NotFoundPage';

export function TemplateEditorPage() {
  const { templateId = '' }: Readonly<Params> = useParams();
  const {
    data: template,
    isPending,
    isError,
    error,
  }: UseQueryResult<Template> = useTemplate(templateId);
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();

  useEffect(() => {
    function ignoreFileDropOutsideDropZones(event: DragEvent) {
      const carriesFiles: boolean = event.dataTransfer?.types.includes('Files') ?? false;
      if (!carriesFiles || event.defaultPrevented) return;
      event.preventDefault();
      if (event.dataTransfer !== null) event.dataTransfer.dropEffect = 'none';
    }
    window.addEventListener('dragover', ignoreFileDropOutsideDropZones);
    window.addEventListener('drop', ignoreFileDropOutsideDropZones);
    return () => {
      window.removeEventListener('dragover', ignoreFileDropOutsideDropZones);
      window.removeEventListener('drop', ignoreFileDropOutsideDropZones);
    };
  }, []);

  if (!isTemplateId(templateId)) return <NotFoundPage />;

  return (
    <PageContainer
      width="app"
      className={cn(
        'flex flex-col items-start gap-6 lg:gap-4 lg:py-6',
        FILL_HEIGHT_UNDER_HEADER_ON_LARGE_SCREEN_CLASS,
      )}
    >
      <Link to={ROUTES.TEMPLATES} className={cn(textLinkClassName, 'text-sm')}>
        {t('templates.editor.back')}
      </Link>
      {isPending && <LoadingSkeleton shape="board" />}
      {isError && <ErrorMessage>{translateError(t, error)}</ErrorMessage>}
      {template && (
        <>
          <div className="flex w-full flex-wrap items-start justify-between gap-4">
            <h1 className="text-2xl font-semibold">{template.name}</h1>
            {template.moderation !== 'hidden' && (
              <CreateRoomButton templateId={template.id} templateName={template.name} />
            )}
          </div>
          {template.moderation === 'hidden' && (
            <TemplateHiddenNotice reason={template.moderation_reason} />
          )}
          <div className="grid w-full max-w-xl items-start gap-4 lg:max-w-none lg:grid-cols-2">
            <TemplateNameField template={template} />
            <TemplateVisibilityField template={template} />
          </div>
          <div
            className={cn(
              'grid w-full gap-8 lg:min-h-0 lg:flex-1 lg:grid-rows-[minmax(0,1fr)]',
              EDITOR_COLUMNS_FITTING_FULL_TIER_ROW_CLASS,
            )}
          >
            <TierEditor template={template} />
            <TileEditor template={template} />
          </div>
        </>
      )}
    </PageContainer>
  );
}
