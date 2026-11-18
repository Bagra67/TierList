import {
  type InfiniteData,
  type QueryClient,
  useInfiniteQuery,
  type UseInfiniteQueryResult,
  useMutation,
  type UseMutationResult,
  useQuery,
  useQueryClient,
  type UseQueryResult,
} from '@tanstack/react-query';

import {
  isTemplateId,
  MARKETPLACE_LIST_QUERY_KEY,
  MARKETPLACE_TAGS_QUERY_KEY,
  publicTemplateQueryKey,
} from '../constants/templates';
import { apiClient, dataOrThrow } from './client';
import { nextCursor } from './pagination';
import { retryUnlessClientError } from './queryClient';
import type { components } from './schema';

export type PublicTemplate = components['schemas']['PublicTemplateResponse'];
export type PublicTile = components['schemas']['PublicTileResponse'];

async function getPublicTemplate(templateId: string, signal: AbortSignal): Promise<PublicTemplate> {
  return dataOrThrow(
    await apiClient.GET('/marketplace/templates/{template_id}', {
      params: { path: { template_id: templateId } },
      signal,
    }),
  );
}

export function usePublicTemplate(templateId: string): UseQueryResult<PublicTemplate> {
  return useQuery({
    queryKey: publicTemplateQueryKey(templateId),
    queryFn: ({ signal }) => getPublicTemplate(templateId, signal),
    enabled: isTemplateId(templateId),
    retry: retryUnlessClientError,
  });
}

export type LikeState = components['schemas']['LikeStateResponse'];

function likeStateQueryKey(templateId: string): readonly string[] {
  return [...publicTemplateQueryKey(templateId), 'like'];
}

async function getLikeState(templateId: string, signal: AbortSignal): Promise<LikeState> {
  return dataOrThrow(
    await apiClient.GET('/marketplace/templates/{template_id}/like', {
      params: { path: { template_id: templateId } },
      signal,
    }),
  );
}

export function useLikeState(templateId: string, enabled: boolean): UseQueryResult<LikeState> {
  return useQuery({
    queryKey: likeStateQueryKey(templateId),
    queryFn: ({ signal }) => getLikeState(templateId, signal),
    enabled,
    retry: retryUnlessClientError,
  });
}

async function setLiked(templateId: string, liked: boolean): Promise<LikeState> {
  const params = { params: { path: { template_id: templateId } } };
  return dataOrThrow(
    liked
      ? await apiClient.PUT('/marketplace/templates/{template_id}/like', params)
      : await apiClient.DELETE('/marketplace/templates/{template_id}/like', params),
  );
}

export function useSetLiked(templateId: string): UseMutationResult<LikeState, Error, boolean> {
  const queryClient: QueryClient = useQueryClient();
  return useMutation({
    mutationFn: (liked: boolean) => setLiked(templateId, liked),
    onSuccess: (state: LikeState) => {
      queryClient.setQueryData(likeStateQueryKey(templateId), state);
      queryClient.setQueryData(
        publicTemplateQueryKey(templateId),
        (template: PublicTemplate | undefined) =>
          template === undefined ? undefined : { ...template, like_count: state.like_count },
      );
    },
  });
}

export type MarketplaceTemplate = components['schemas']['MarketplaceTemplateResponse'];
type MarketplaceTemplateList = components['schemas']['MarketplaceTemplateListResponse'];
export type MarketplaceSort = 'popular' | 'newest';

export interface MarketplaceFilters {
  search?: string;
  tag?: string;
  sort: MarketplaceSort;
}

async function listMarketplaceTemplates(
  filters: MarketplaceFilters,
  cursor: string | undefined,
  limit: number | undefined,
  signal: AbortSignal,
): Promise<MarketplaceTemplateList> {
  return dataOrThrow(
    await apiClient.GET('/marketplace/templates', {
      params: { query: { q: filters.search, tag: filters.tag, sort: filters.sort, cursor, limit } },
      signal,
    }),
  );
}

export function useMarketplaceTemplates(
  filters: MarketplaceFilters,
): UseInfiniteQueryResult<InfiniteData<MarketplaceTemplateList, string | undefined>> {
  return useInfiniteQuery({
    queryKey: [...MARKETPLACE_LIST_QUERY_KEY, filters],
    queryFn: ({ pageParam, signal }) =>
      listMarketplaceTemplates(filters, pageParam, undefined, signal),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: nextCursor,
    retry: retryUnlessClientError,
  });
}

export function usePopularTemplates(count: number): UseQueryResult<MarketplaceTemplate[]> {
  return useQuery({
    queryKey: [...MARKETPLACE_LIST_QUERY_KEY, 'popular', count],
    queryFn: async ({ signal }) =>
      (await listMarketplaceTemplates({ sort: 'popular' }, undefined, count, signal)).items,
    retry: retryUnlessClientError,
  });
}

export function useMarketplaceTags(): UseQueryResult<string[]> {
  return useQuery({
    queryKey: MARKETPLACE_TAGS_QUERY_KEY,
    queryFn: async ({ signal }) =>
      dataOrThrow(await apiClient.GET('/marketplace/tags', { signal })).tags,
    retry: retryUnlessClientError,
  });
}

export function uniqueById<Item extends { id: string }>(items: Item[]): Item[] {
  const seen: Set<string> = new Set();
  return items.filter((item: Item) => {
    if (seen.has(item.id)) return false;
    seen.add(item.id);
    return true;
  });
}
