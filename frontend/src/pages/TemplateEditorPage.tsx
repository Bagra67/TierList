import type { UseQueryResult } from '@tanstack/react-query';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';
import { Link, type Params, useParams } from 'react-router';

import { type Template, useTemplate } from '../api/templates';
import { ErrorMessage } from '../components/ErrorMessage';
import { TemplateNameField } from '../components/TemplateNameField';
import { TierEditor } from '../components/TierEditor';
import { TileEditor } from '../components/TileEditor';
import { ROUTES } from '../constants/routes';
import { translateError } from '../errors/apiError';

// Éditeur d'un template : son nom, ses tiers (US-1.4) et ses tuiles texte (US-1.2, US-1.3)
export function TemplateEditorPage() {
  // Toujours présent : la route TEMPLATE_EDITOR déclare ce paramètre
  const { templateId = '' }: Readonly<Params> = useParams();
  const {
    data: template,
    isPending,
    isError,
    error,
  }: UseQueryResult<Template> = useTemplate(templateId);
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-col items-start gap-6 px-4 py-10">
      <Link to={ROUTES.TEMPLATES} className="text-sm underline underline-offset-4">
        {t('templates.editor.back')}
      </Link>
      {isPending && <p className="text-muted-foreground">{t('common.loading')}</p>}
      {isError && <ErrorMessage>{translateError(t, error)}</ErrorMessage>}
      {template && (
        <>
          <h1 className="text-2xl font-semibold">{template.name}</h1>
          <TemplateNameField template={template} />
          <TierEditor template={template} />
          <TileEditor template={template} />
        </>
      )}
    </main>
  );
}
