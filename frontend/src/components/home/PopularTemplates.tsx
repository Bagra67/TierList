import { useId } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import {
  type MarketplaceTemplate,
  useCardLikeStates,
  usePopularTemplates,
} from '../../api/marketplace';
import { HOME_POPULAR_COUNT } from '../../constants/home';
import { ROUTES } from '../../constants/routes';
import { MarketplaceCard } from '../MarketplaceCard';
import { Button } from '../ui/button';

export function PopularTemplates() {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const headingId: string = useId();
  const { data: templates } = usePopularTemplates(HOME_POPULAR_COUNT);
  useCardLikeStates(templates === undefined ? [] : [templates]);

  if (templates === undefined || templates.length === 0) return null;
  return (
    <section aria-labelledby={headingId} className="flex w-full flex-col items-start gap-4">
      <h2 id={headingId} className="text-lg font-semibold">
        {t('home.popular.title')}
      </h2>
      <ul className="grid w-full gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {templates.map((template: MarketplaceTemplate) => (
          <MarketplaceCard key={template.id} template={template} />
        ))}
      </ul>
      <Button asChild variant="outline">
        <Link to={ROUTES.MARKETPLACE}>{t('home.popular.all')}</Link>
      </Button>
    </section>
  );
}
