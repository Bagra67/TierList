import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import { translateError } from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { LoadingSkeleton } from './LoadingSkeleton';
import { Button } from './ui/button';

interface PagedQuery {
  data: unknown;
  isPending: boolean;
  isError: boolean;
  error: Error | null;
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  fetchNextPage: () => Promise<unknown>;
}

interface PagedListProps {
  query: PagedQuery;
  itemCount: number;
  empty: ReactNode;
  moreLabel: string;
  children: ReactNode;
}

export function PagedList({ query, itemCount, empty, moreLabel, children }: PagedListProps) {
  const { t } = useTranslation();

  return (
    <>
      {query.isPending && <LoadingSkeleton shape="list" />}
      {query.isError && <ErrorMessage>{translateError(t, query.error)}</ErrorMessage>}
      {query.data !== undefined && itemCount === 0 && empty}
      {itemCount > 0 && children}
      {query.hasNextPage && (
        <Button
          type="button"
          variant="outline"
          disabled={query.isFetchingNextPage}
          onClick={() => void query.fetchNextPage()}
        >
          {query.isFetchingNextPage ? t('common.loading') : moreLabel}
        </Button>
      )}
    </>
  );
}
