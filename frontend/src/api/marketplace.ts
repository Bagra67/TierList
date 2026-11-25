import {
  type InfiniteData,
  type QueryClient,
  useInfiniteQuery,
  type UseInfiniteQueryResult,
  useMutation,
  type UseMutationResult,
  useQueries,
  useQuery,
  useQueryClient,
  type UseQueryResult,
} from '@tanstack/react-query';

import {
  CARD_STATES_STALE_MS,
  FAVORITE_TEMPLATES_QUERY_KEY,
  isTemplateId,
  MARKETPLACE_FAVORITE_STATES_QUERY_KEY,
  MARKETPLACE_LIKE_STATES_QUERY_KEY,
  MARKETPLACE_LIST_QUERY_KEY,
  MARKETPLACE_TAGS_QUERY_KEY,
  publicTemplateQueryKey,
} from '../constants/templates';
import { useCurrentUser } from './auth';
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

export type LineageAncestor = components['schemas']['LineageAncestorResponse'];
type CopyState = components['schemas']['CopyStateResponse'];

async function getCopyState(templateId: string, signal: AbortSignal): Promise<CopyState> {
  return dataOrThrow(
    await apiClient.GET('/marketplace/templates/{template_id}/copy', {
      params: { path: { template_id: templateId } },
      signal,
    }),
  );
}

export function useCopyState(templateId: string, enabled: boolean): UseQueryResult<CopyState> {
  return useQuery({
    queryKey: [...publicTemplateQueryKey(templateId), 'copy'],
    queryFn: ({ signal }) => getCopyState(templateId, signal),
    enabled,
    retry: retryUnlessClientError,
  });
}

export type FavoriteState = components['schemas']['FavoriteStateResponse'];

function favoriteStateQueryKey(templateId: string): readonly string[] {
  return [...publicTemplateQueryKey(templateId), 'favorite'];
}

async function getFavoriteState(templateId: string, signal: AbortSignal): Promise<FavoriteState> {
  return dataOrThrow(
    await apiClient.GET('/marketplace/templates/{template_id}/favorite', {
      params: { path: { template_id: templateId } },
      signal,
    }),
  );
}

export function useFavoriteState(
  templateId: string,
  enabled: boolean,
): UseQueryResult<FavoriteState> {
  return useQuery({
    queryKey: favoriteStateQueryKey(templateId),
    queryFn: ({ signal }) => getFavoriteState(templateId, signal),
    enabled,
    retry: retryUnlessClientError,
  });
}

async function setFavorited(templateId: string, favorited: boolean): Promise<FavoriteState> {
  const params = { params: { path: { template_id: templateId } } };
  return dataOrThrow(
    favorited
      ? await apiClient.PUT('/marketplace/templates/{template_id}/favorite', params)
      : await apiClient.DELETE('/marketplace/templates/{template_id}/favorite', params),
  );
}

export function useSetFavorited(
  templateId: string,
): UseMutationResult<FavoriteState, Error, boolean> {
  const queryClient: QueryClient = useQueryClient();
  return useMutation({
    mutationFn: (favorited: boolean) => setFavorited(templateId, favorited),
    onSuccess: (state: FavoriteState) => {
      queryClient.setQueryData(favoriteStateQueryKey(templateId), state);
      if (!state.favorited) {
        queryClient.setQueryData(
          FAVORITE_TEMPLATES_QUERY_KEY,
          (favorites: FavoriteTemplatePages | undefined) =>
            favorites === undefined ? undefined : withoutTemplate(favorites, templateId),
        );
      }
      void queryClient.invalidateQueries({
        queryKey: FAVORITE_TEMPLATES_QUERY_KEY,
        refetchType: 'none',
      });
    },
  });
}

type TemplateLikeState = components['schemas']['TemplateLikeStateResponse'];
type TemplateFavoriteState = components['schemas']['TemplateFavoriteStateResponse'];

async function listLikeStates(
  templateIds: string[],
  signal: AbortSignal,
): Promise<TemplateLikeState[]> {
  return dataOrThrow(
    await apiClient.GET('/marketplace/likes', {
      params: { query: { template_id: templateIds } },
      signal,
    }),
  ).items;
}

async function listFavoriteStates(
  templateIds: string[],
  signal: AbortSignal,
): Promise<TemplateFavoriteState[]> {
  return dataOrThrow(
    await apiClient.GET('/marketplace/favorite-states', {
      params: { query: { template_id: templateIds } },
      signal,
    }),
  ).items;
}

interface CardStateSource<State extends { template_id: string }> {
  queryKey: readonly string[];
  list: (templateIds: string[], signal: AbortSignal) => Promise<State[]>;
  stateQueryKey: (templateId: string) => readonly string[];
}

function useCardStatesOf<State extends { template_id: string }>(
  pages: MarketplaceTemplate[][],
  source: CardStateSource<State>,
): void {
  const queryClient: QueryClient = useQueryClient();
  const { data: user } = useCurrentUser();
  useQueries({
    queries: pages.map((templates: MarketplaceTemplate[]) => {
      const templateIds: string[] = templates.map((template: MarketplaceTemplate) => template.id);
      return {
        queryKey: [...source.queryKey, templateIds],
        queryFn: async ({ signal }: { signal: AbortSignal }) => {
          const states: State[] = await source.list(templateIds, signal);
          for (const { template_id: templateId, ...state } of states) {
            queryClient.setQueryData(source.stateQueryKey(templateId), state);
          }
          return templateIds;
        },
        enabled: Boolean(user) && templateIds.length > 0,
        staleTime: CARD_STATES_STALE_MS,
        refetchOnWindowFocus: false,
        retry: retryUnlessClientError,
      };
    }),
  });
}

export function useCardLikeStates(pages: MarketplaceTemplate[][]): void {
  useCardStatesOf(pages, {
    queryKey: MARKETPLACE_LIKE_STATES_QUERY_KEY,
    list: listLikeStates,
    stateQueryKey: likeStateQueryKey,
  });
}

export function useCardStates(pages: MarketplaceTemplate[][]): void {
  useCardLikeStates(pages);
  useCardStatesOf(pages, {
    queryKey: MARKETPLACE_FAVORITE_STATES_QUERY_KEY,
    list: listFavoriteStates,
    stateQueryKey: favoriteStateQueryKey,
  });
}

export type MarketplaceTemplate = components['schemas']['MarketplaceTemplateResponse'];
type MarketplaceTemplateList = components['schemas']['MarketplaceTemplateListResponse'];
export type MarketplaceSort = components['schemas']['MarketplaceSort'];

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

async function listFeaturedTemplates(signal: AbortSignal): Promise<MarketplaceTemplate[]> {
  return dataOrThrow(await apiClient.GET('/marketplace/featured', { signal })).items;
}

export function uniqueById<Item extends { id: string }>(items: Item[]): Item[] {
  const seen: Set<string> = new Set();
  return items.filter((item: Item) => {
    if (seen.has(item.id)) return false;
    seen.add(item.id);
    return true;
  });
}

export function useFeaturedTemplates(): UseQueryResult<MarketplaceTemplate[]> {
  return useQuery({
    queryKey: [...MARKETPLACE_LIST_QUERY_KEY, 'featured'],
    queryFn: ({ signal }) => listFeaturedTemplates(signal),
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

type FavoriteTemplatePages = InfiniteData<MarketplaceTemplateList, string | undefined>;

const FAVORITED_STATE: FavoriteState = { favorited: true, can_favorite: true };

function withoutTemplate(
  favorites: FavoriteTemplatePages,
  templateId: string,
): FavoriteTemplatePages {
  return {
    ...favorites,
    pages: favorites.pages.map((page: MarketplaceTemplateList) => ({
      ...page,
      items: page.items.filter((template: MarketplaceTemplate) => template.id !== templateId),
    })),
  };
}

async function listFavoriteTemplates(
  cursor: string | undefined,
  signal: AbortSignal,
): Promise<MarketplaceTemplateList> {
  return dataOrThrow(
    await apiClient.GET('/marketplace/favorites', { params: { query: { cursor } }, signal }),
  );
}

export function useFavoriteTemplates(): UseInfiniteQueryResult<FavoriteTemplatePages> {
  const queryClient: QueryClient = useQueryClient();
  return useInfiniteQuery({
    queryKey: FAVORITE_TEMPLATES_QUERY_KEY,
    queryFn: async ({ pageParam, signal }) => {
      const page: MarketplaceTemplateList = await listFavoriteTemplates(pageParam, signal);
      for (const template of page.items) {
        queryClient.setQueryData(favoriteStateQueryKey(template.id), FAVORITED_STATE);
      }
      return page;
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: nextCursor,
    retry: retryUnlessClientError,
  });
}
