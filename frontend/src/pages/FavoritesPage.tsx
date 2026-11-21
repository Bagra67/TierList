import { type UseTranslationResponse, useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import { type MarketplaceTemplate, useCardStates, useFavoriteTemplates } from '../api/marketplace';
import { EmptyState } from '../components/EmptyState';
import { MarketplaceCard } from '../components/MarketplaceCard';
import { PageContainer } from '../components/PageContainer';
import { PagedList } from '../components/PagedList';
import { Button } from '../components/ui/button';
import { useDocumentTitle } from '../components/useDocumentTitle';
import { ROUTES } from '../constants/routes';

export function FavoritesPage() {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  useDocumentTitle(t('favorites.title'));
  const query = useFavoriteTemplates();
  const pages: MarketplaceTemplate[][] = query.data?.pages.map((page) => page.items) ?? [];
  useCardStates(pages);
  const templates: MarketplaceTemplate[] = pages.flat();

  return (
    <PageContainer width="app" className="flex flex-col items-start gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">{t('favorites.title')}</h1>
        <p className="max-w-2xl text-muted-foreground">{t('favorites.intro')}</p>
      </div>
      <PagedList
        query={query}
        itemCount={templates.length}
        empty={
          <EmptyState
            message={t('favorites.empty')}
            action={
              <Button asChild variant="outline">
                <Link to={ROUTES.MARKETPLACE}>{t('favorites.emptyAction')}</Link>
              </Button>
            }
          />
        }
        moreLabel={t('favorites.more')}
      >
        <ul className="grid w-full gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {templates.map((template: MarketplaceTemplate) => (
            <MarketplaceCard key={template.id} template={template} />
          ))}
        </ul>
      </PagedList>
    </PageContainer>
  );
}
