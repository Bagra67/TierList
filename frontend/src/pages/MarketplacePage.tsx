import { type FormEvent, useId, useState } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';
import { type SetURLSearchParams, useSearchParams } from 'react-router';

import {
  type MarketplaceFilters,
  type MarketplaceSort,
  type MarketplaceTemplate,
  uniqueById,
  useCardLikeStates,
  useFeaturedTemplates,
  useMarketplaceTags,
  useMarketplaceTemplates,
} from '../api/marketplace';
import { EmptyState } from '../components/EmptyState';
import { MarketplaceCard } from '../components/MarketplaceCard';
import { PageContainer } from '../components/PageContainer';
import { PagedList } from '../components/PagedList';
import { tagPillClassName } from '../components/TemplateTagList';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { NativeSelect } from '../components/ui/native-select';
import { useDocumentTitle } from '../components/useDocumentTitle';
import { MARKETPLACE_SEARCH_MAX_LENGTH } from '../constants/marketplace';
import {
  MARKETPLACE_SEARCH_PARAM,
  MARKETPLACE_SORT_PARAM,
  MARKETPLACE_TAG_PARAM,
} from '../constants/routes';
import { cn } from 'cn';

const DEFAULT_SORT: MarketplaceSort = 'popular';
const SORTS: readonly MarketplaceSort[] = ['popular', 'newest'];

function filtersOf(searchParams: URLSearchParams): MarketplaceFilters {
  const sort: string | null = searchParams.get(MARKETPLACE_SORT_PARAM);
  return {
    search: searchParams.get(MARKETPLACE_SEARCH_PARAM) || undefined,
    tag: searchParams.get(MARKETPLACE_TAG_PARAM) || undefined,
    sort: SORTS.find((known: MarketplaceSort) => known === sort) ?? DEFAULT_SORT,
  };
}

function withParam(
  searchParams: URLSearchParams,
  name: string,
  value: string | undefined,
): URLSearchParams {
  const next: URLSearchParams = new URLSearchParams(searchParams);
  if (value === undefined || value === '') next.delete(name);
  else next.set(name, value);
  return next;
}

export function MarketplacePage() {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  useDocumentTitle(t('marketplace.title'));
  const [searchParams, setSearchParams]: [URLSearchParams, SetURLSearchParams] = useSearchParams();
  const filters: MarketplaceFilters = filtersOf(searchParams);
  const query = useMarketplaceTemplates(filters);
  const { data: featured = [] } = useFeaturedTemplates();
  const pages: MarketplaceTemplate[][] = query.data?.pages.map((page) => page.items) ?? [];
  const [firstPage = [], ...nextPages]: MarketplaceTemplate[][] = pages;
  useCardLikeStates([uniqueById([...featured, ...firstPage]), ...nextPages]);
  const templates: MarketplaceTemplate[] = uniqueById(pages.flat());
  const hasFilter: boolean = filters.search !== undefined || filters.tag !== undefined;

  return (
    <PageContainer width="app" className="flex flex-col items-start gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">{t('marketplace.title')}</h1>
        <p className="max-w-2xl text-muted-foreground">{t('marketplace.intro')}</p>
      </div>
      <MarketplaceControls
        key={filters.search ?? ''}
        filters={filters}
        onChange={(name: string, value: string | undefined) =>
          setSearchParams(withParam(searchParams, name, value))
        }
      />
      {!hasFilter && featured.length > 0 && <TierListPicks templates={featured} />}
      <PagedList
        query={query}
        itemCount={templates.length}
        empty={
          <EmptyState
            message={hasFilter ? t('marketplace.noMatch') : t('marketplace.empty')}
            action={
              hasFilter ? (
                <Button type="button" variant="outline" onClick={() => setSearchParams({})}>
                  {t('marketplace.clear')}
                </Button>
              ) : undefined
            }
          />
        }
        moreLabel={t('marketplace.more')}
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

function TierListPicks({ templates }: { templates: MarketplaceTemplate[] }) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const headingId: string = useId();
  return (
    <section
      aria-labelledby={headingId}
      className="flex w-full flex-col gap-4 rounded-panel bg-muted p-4 sm:p-5"
    >
      <div className="flex flex-col gap-1">
        <h2 id={headingId} className="text-lg font-semibold">
          {t('marketplace.picks.title')}
        </h2>
        <p className="text-sm text-muted-foreground">{t('marketplace.picks.intro')}</p>
      </div>
      <ul className="grid w-full gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {templates.map((template: MarketplaceTemplate) => (
          <MarketplaceCard key={template.id} template={template} showFeaturedBadge={false} />
        ))}
      </ul>
    </section>
  );
}

interface MarketplaceControlsProps {
  filters: MarketplaceFilters;
  onChange: (name: string, value: string | undefined) => void;
}

function MarketplaceControls({ filters, onChange }: MarketplaceControlsProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const searchId: string = useId();
  const sortId: string = useId();
  const [searchDraft, setSearchDraft] = useState<string>(filters.search ?? '');
  const { data: tags } = useMarketplaceTags();

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onChange(MARKETPLACE_SEARCH_PARAM, searchDraft.trim());
  }

  return (
    <div className="flex w-full flex-col gap-4">
      <div className="flex w-full flex-wrap items-end gap-4">
        <form
          role="search"
          onSubmit={handleSubmit}
          className="flex w-full min-w-0 flex-col gap-2 sm:w-auto sm:max-w-xl sm:flex-1"
        >
          <Label htmlFor={searchId}>{t('marketplace.search.label')}</Label>
          <div className="flex gap-2">
            <Input
              id={searchId}
              type="search"
              value={searchDraft}
              maxLength={MARKETPLACE_SEARCH_MAX_LENGTH}
              onChange={(event) => setSearchDraft(event.target.value)}
            />
            <Button type="submit">{t('marketplace.search.submit')}</Button>
          </div>
        </form>
        <div className="flex flex-col gap-2">
          <Label htmlFor={sortId}>{t('marketplace.sort.label')}</Label>
          <NativeSelect
            id={sortId}
            value={filters.sort}
            onChange={(event) =>
              onChange(
                MARKETPLACE_SORT_PARAM,
                event.target.value === DEFAULT_SORT ? undefined : event.target.value,
              )
            }
          >
            {SORTS.map((sort: MarketplaceSort) => (
              <option key={sort} value={sort}>
                {t(`marketplace.sort.${sort}`)}
              </option>
            ))}
          </NativeSelect>
        </div>
      </div>
      {tags !== undefined && tags.length > 0 && (
        <ul aria-label={t('marketplace.tags.label')} className="flex flex-wrap gap-2">
          {tags.map((tag: string) => {
            const active: boolean = filters.tag?.toLowerCase() === tag.toLowerCase();
            return (
              <li key={tag}>
                <button
                  type="button"
                  aria-pressed={active}
                  onClick={() => onChange(MARKETPLACE_TAG_PARAM, active ? undefined : tag)}
                  className={cn(
                    tagPillClassName,
                    'px-3 py-1 text-sm font-medium outline-none focus-visible:ring-3 focus-visible:ring-ring',
                    active && 'bg-foreground text-background',
                  )}
                >
                  {tag}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
