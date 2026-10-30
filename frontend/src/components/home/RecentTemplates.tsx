import { useId } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import { type TemplateSummary, useTemplates } from '../../api/templates';
import { HOME_RECENT_COUNT } from '../../constants/home';
import { ROUTES, templateEditorPath } from '../../constants/routes';
import { translateError } from '../../errors/apiError';
import { CreateRoomButton } from '../CreateRoomButton';
import { EmptyState } from '../EmptyState';
import { ErrorMessage } from '../ErrorMessage';
import { LoadingSkeleton } from '../LoadingSkeleton';
import { Button } from '../ui/button';
import { panelVariants } from '../ui/panel';
import { textLinkClassName } from '../ui/text-link';

// Accueil connecté : les derniers modèles modifiés (l'API les trie ainsi), chacun avec de quoi
// ouvrir une salle tout de suite
export function RecentTemplates() {
  const { data: templates, isPending, isError, error } = useTemplates();
  const { t } = useTranslation();
  const headingId: string = useId();

  return (
    <section aria-labelledby={headingId} className="flex min-w-0 flex-col items-start gap-3">
      <div className="flex w-full flex-wrap items-baseline justify-between gap-2">
        <h2 id={headingId} className="text-lg font-semibold">
          {t('home.recentTemplates.title')}
        </h2>
        {templates !== undefined && templates.length > 0 && (
          <Link to={ROUTES.TEMPLATES} className={textLinkClassName}>
            {t('home.recentTemplates.all')}
          </Link>
        )}
      </div>
      {isPending && <LoadingSkeleton shape="list" />}
      {isError && <ErrorMessage>{translateError(t, error)}</ErrorMessage>}
      {templates?.length === 0 && (
        <EmptyState
          message={t('home.recentTemplates.empty')}
          action={
            <Button asChild>
              <Link to={ROUTES.TEMPLATES}>{t('home.prepareTemplate')}</Link>
            </Button>
          }
        />
      )}
      {templates !== undefined && templates.length > 0 && (
        <ul className={panelVariants({ variant: 'list' })}>
          {templates.slice(0, HOME_RECENT_COUNT).map((template: TemplateSummary) => (
            <li key={template.id} className="flex items-center justify-between gap-4 px-4 py-3">
              <div className="flex min-w-0 flex-col gap-1">
                <Link
                  to={templateEditorPath(template.id)}
                  className="truncate font-medium underline-offset-4 hover:underline"
                >
                  {template.name}
                </Link>
                <span className="text-sm text-muted-foreground">
                  {t('templates.tileCount', { count: template.tile_count })}
                </span>
              </div>
              <CreateRoomButton templateId={template.id} templateName={template.name} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
