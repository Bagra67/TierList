import { useId } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router';

import { useTemplate } from '../api/templates';
import { ErrorMessage } from '../components/ErrorMessage';
import { ROUTES } from '../constants/routes';
import { translateError } from '../errors/apiError';

// Éditeur d'un template : pour l'instant en lecture seule (nom et tiers). La configuration des
// tiers (#79) et des tuiles (#80) viendra s'y ajouter.
export function TemplateEditorPage() {
  // Toujours présent : la route TEMPLATE_EDITOR déclare ce paramètre
  const { templateId = '' } = useParams();
  const { data: template, isPending, isError, error } = useTemplate(templateId);
  const { t } = useTranslation();
  const tiersTitleId = useId();

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
          <section aria-labelledby={tiersTitleId} className="flex w-full flex-col gap-2">
            <h2 id={tiersTitleId} className="text-lg font-semibold">
              {t('templates.editor.tiers')}
            </h2>
            <ol className="flex w-full flex-col gap-1">
              {template.tiers.map((tier) => (
                <li key={tier.id} className="flex items-center gap-3 rounded-md border px-3 py-2">
                  <span
                    aria-hidden="true"
                    className="size-4 rounded-full"
                    style={{ backgroundColor: tier.color }}
                  />
                  {tier.name}
                </li>
              ))}
            </ol>
          </section>
        </>
      )}
    </main>
  );
}
