import {
  type InfiniteData,
  type UseInfiniteQueryResult,
  useInfiniteQuery,
} from '@tanstack/react-query';

import { apiClient, dataOrThrow } from './client';
import { retryUnlessClientError } from './queryClient';
import type { components } from './schema';

export type HistoryPage = components['schemas']['HistoryResponse'];

const HISTORY_QUERY_KEY = ['history'] as const;

// Une page de l'historique du compte connecté, à partir de offset (US-5.5). La taille de page est
// celle du backend : la page suivante commence après les parties déjà lues
async function getHistory(offset: number, signal: AbortSignal): Promise<HistoryPage> {
  return dataOrThrow(await apiClient.GET('/history', { params: { query: { offset } }, signal }));
}

// L'historique page par page : « Voir plus » lit la page suivante tant que le backend en annonce
export function useHistory(): UseInfiniteQueryResult<InfiniteData<HistoryPage, number>> {
  return useInfiniteQuery({
    queryKey: HISTORY_QUERY_KEY,
    queryFn: ({ pageParam, signal }) => getHistory(pageParam, signal),
    initialPageParam: 0,
    getNextPageParam: (lastPage: HistoryPage, pages: HistoryPage[]) =>
      lastPage.has_more
        ? pages.reduce((count: number, page: HistoryPage) => count + page.games.length, 0)
        : undefined,
    retry: retryUnlessClientError,
  });
}
