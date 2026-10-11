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

// Éditeur d'un template : son nom, ses tiers (US-1.4) et ses tuiles (US-1.2, US-1.3). Sur grand
// écran, les tiers sont à gauche et la grille des tuiles à droite, pour profiter de la largeur
// plutôt que d'empiler toute la page.
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
    <main className="mx-auto flex w-full max-w-7xl flex-col items-start gap-6 px-4 py-10">
      <Link to={ROUTES.TEMPLATES} className="text-sm underline underline-offset-4">
        {t('templates.editor.back')}
      </Link>
      {isPending && <p className="text-muted-foreground">{t('common.loading')}</p>}
      {isError && <ErrorMessage>{translateError(t, error)}</ErrorMessage>}
      {template && (
        <>
          <h1 className="text-2xl font-semibold">{template.name}</h1>
          {/* Un nom n'a pas besoin de toute la largeur de la page */}
          <div className="w-full max-w-xl">
            <TemplateNameField template={template} />
          </div>
          {/* 22rem : la poignée, la pastille, le nom et les trois boutons d'un tier */}
          <div className="grid w-full gap-8 lg:grid-cols-[22rem_minmax(0,1fr)] lg:items-start">
            <TierEditor template={template} />
            <TileEditor template={template} />
          </div>
        </>
      )}
    </main>
  );
}
