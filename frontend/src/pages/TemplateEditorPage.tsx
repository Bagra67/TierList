import type { UseQueryResult } from '@tanstack/react-query';
import { useEffect } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';
import { Link, type Params, useParams } from 'react-router';

import { type Template, useTemplate } from '../api/templates';
import { CreateRoomButton } from '../components/CreateRoomButton';
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

  // Un fichier lâché à côté d'une vignette d'image serait ouvert par le navigateur, qui quitterait
  // l'éditeur : hors des vignettes (qui gèrent elles-mêmes le dépôt), il est ignoré
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

  return (
    // Sur grand écran, l'éditeur remplit exactement la hauteur sous l'en-tête : la page ne défile
    // pas, ce sont la colonne des tiers et la grille des tuiles qui défilent (chacune de son côté)
    <main className="mx-auto flex w-full max-w-7xl flex-col items-start gap-6 px-4 py-10 lg:min-h-0 lg:flex-1 lg:gap-4 lg:py-6">
      <Link to={ROUTES.TEMPLATES} className="text-sm underline underline-offset-4">
        {t('templates.editor.back')}
      </Link>
      {isPending && <p className="text-muted-foreground">{t('common.loading')}</p>}
      {isError && <ErrorMessage>{translateError(t, error)}</ErrorMessage>}
      {template && (
        <>
          <div className="flex w-full flex-wrap items-start justify-between gap-4">
            <h1 className="text-2xl font-semibold">{template.name}</h1>
            <CreateRoomButton templateId={template.id} templateName={template.name} />
          </div>
          {/* Un nom n'a pas besoin de toute la largeur de la page */}
          <div className="w-full max-w-xl">
            <TemplateNameField template={template} />
          </div>
          {/* 22rem : la poignée, la pastille, le nom et les trois boutons d'un tier */}
          <div className="grid w-full gap-8 lg:min-h-0 lg:flex-1 lg:grid-cols-[22rem_minmax(0,1fr)] lg:grid-rows-[minmax(0,1fr)]">
            <TierEditor template={template} />
            <TileEditor template={template} />
          </div>
        </>
      )}
    </main>
  );
}
