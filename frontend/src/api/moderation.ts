import {
  type InfiniteData,
  type UseInfiniteQueryResult,
  type UseQueryResult,
  useInfiniteQuery,
  useQuery,
} from '@tanstack/react-query';

import { apiClient, dataOrThrow } from './client';
import { retryUnlessClientError } from './queryClient';
import type { components } from './schema';

export type ModerationLogPage = components['schemas']['ModerationLogResponse'];
export type ModerationLogEntry = components['schemas']['ModerationActionResponse'];
export type SuperAdmin = components['schemas']['SuperAdminResponse'];

// Filtres du journal : un super admin (son id) et un texte cherché dans le libellé de la cible
export interface ModerationLogFilters {
  actorId?: string;
  target?: string;
}

const MODERATION_LOG_QUERY_KEY = ['moderation', 'log'] as const;
const SUPER_ADMINS_QUERY_KEY = ['moderation', 'super-admins'] as const;

// Une page du journal de modération à partir de offset (US-1.9). La taille de page est celle du
// backend : la page suivante commence après les entrées déjà lues
async function getModerationLog(
  filters: ModerationLogFilters,
  offset: number,
  signal: AbortSignal,
): Promise<ModerationLogPage> {
  return dataOrThrow(
    await apiClient.GET('/moderation/log', {
      params: { query: { offset, actor_id: filters.actorId, target: filters.target } },
      signal,
    }),
  );
}

// Le journal page par page, pour ces filtres : « Voir plus » lit la page suivante tant que le
// backend en annonce. Changer de filtre repart de la première page (autre clé de requête)
export function useModerationLog(
  filters: ModerationLogFilters,
): UseInfiniteQueryResult<InfiniteData<ModerationLogPage, number>> {
  return useInfiniteQuery({
    queryKey: [...MODERATION_LOG_QUERY_KEY, filters],
    queryFn: ({ pageParam, signal }) => getModerationLog(filters, pageParam, signal),
    initialPageParam: 0,
    getNextPageParam: (lastPage: ModerationLogPage, pages: ModerationLogPage[]) =>
      lastPage.has_more
        ? pages.reduce((count: number, page: ModerationLogPage) => count + page.entries.length, 0)
        : undefined,
    retry: retryUnlessClientError,
  });
}

// Les super admins, pour le filtre par auteur du journal
export function useSuperAdmins(): UseQueryResult<SuperAdmin[]> {
  return useQuery({
    queryKey: SUPER_ADMINS_QUERY_KEY,
    queryFn: async ({ signal }) =>
      dataOrThrow(await apiClient.GET('/moderation/super-admins', { signal })),
    retry: retryUnlessClientError,
  });
}
