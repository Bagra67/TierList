import {
  type InfiniteData,
  type UseInfiniteQueryResult,
  useInfiniteQuery,
} from '@tanstack/react-query';

import { HISTORY_QUERY_KEY } from '../constants/results';
import { nextOffset } from './pagination';
import { apiClient, dataOrThrow } from './client';
import { retryUnlessClientError } from './queryClient';
import type { components } from './schema';

export type HistoryPage = components['schemas']['HistoryResponse'];

async function getHistory(offset: number, signal: AbortSignal): Promise<HistoryPage> {
  return dataOrThrow(await apiClient.GET('/history', { params: { query: { offset } }, signal }));
}

export function useHistory(): UseInfiniteQueryResult<InfiniteData<HistoryPage, number>> {
  return useInfiniteQuery({
    queryKey: HISTORY_QUERY_KEY,
    queryFn: ({ pageParam, signal }) => getHistory(pageParam, signal),
    initialPageParam: 0,
    getNextPageParam: nextOffset((page: HistoryPage) => page.games),
    retry: retryUnlessClientError,
  });
}
