import {
  type InfiniteData,
  type UseInfiniteQueryResult,
  type UseQueryResult,
  type QueryClient,
  type UseMutationResult,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';

import { apiClient, dataOrThrow, throwIfError } from './client';
import { retryUnlessClientError } from './queryClient';
import type { components, paths } from './schema';

export type ModerationLogPage = components['schemas']['ModerationLogResponse'];
export type ModerationLogEntry = components['schemas']['ModerationActionResponse'];
export type SuperAdmin = components['schemas']['SuperAdminResponse'];
export type RecentUploadsPage = components['schemas']['RecentUploadsResponse'];
export type RecentUpload = components['schemas']['RecentUploadResponse'];
export type ListedImageStatus = NonNullable<
  NonNullable<paths['/moderation/images']['get']['parameters']['query']>['status']
>;
export type ImageModerationAction = 'hide' | 'unhide' | 'delete';
export type TemplateModerationAction = ImageModerationAction;
export type AccountSearchPage = components['schemas']['AccountSearchResponse'];
export type AccountSummary = components['schemas']['AccountSummaryResponse'];
export type Account = components['schemas']['AccountResponse'];

export interface ModerationLogFilters {
  actorId?: string;
  target?: string;
  accountId?: string;
}

const MODERATION_LOG_QUERY_KEY = ['moderation', 'log'] as const;
const SUPER_ADMINS_QUERY_KEY = ['moderation', 'super-admins'] as const;
const RECENT_UPLOADS_QUERY_KEY = ['moderation', 'images'] as const;
const ACCOUNT_SEARCH_QUERY_KEY = ['moderation', 'accounts', 'search'] as const;
const ACCOUNT_QUERY_KEY = ['moderation', 'accounts', 'detail'] as const;

export interface RecentUploadsFilters {
  author?: string;
  createdAfter?: string;
  createdBefore?: string;
  status?: ListedImageStatus;
  ownerId?: string;
}

async function getModerationLog(
  filters: ModerationLogFilters,
  offset: number,
  signal: AbortSignal,
): Promise<ModerationLogPage> {
  return dataOrThrow(
    await apiClient.GET('/moderation/log', {
      params: {
        query: {
          offset,
          actor_id: filters.actorId,
          target: filters.target,
          account_id: filters.accountId,
        },
      },
      signal,
    }),
  );
}

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

export function useSuperAdmins(): UseQueryResult<SuperAdmin[]> {
  return useQuery({
    queryKey: SUPER_ADMINS_QUERY_KEY,
    queryFn: async ({ signal }) =>
      dataOrThrow(await apiClient.GET('/moderation/super-admins', { signal })),
    retry: retryUnlessClientError,
  });
}

async function getRecentUploads(
  filters: RecentUploadsFilters,
  offset: number,
  signal: AbortSignal,
): Promise<RecentUploadsPage> {
  return dataOrThrow(
    await apiClient.GET('/moderation/images', {
      params: {
        query: {
          offset,
          author: filters.author,
          created_after: filters.createdAfter,
          created_before: filters.createdBefore,
          status: filters.status,
          owner_id: filters.ownerId,
        },
      },
      signal,
    }),
  );
}

export function useRecentUploads(
  filters: RecentUploadsFilters,
): UseInfiniteQueryResult<InfiniteData<RecentUploadsPage, number>> {
  return useInfiniteQuery({
    queryKey: [...RECENT_UPLOADS_QUERY_KEY, filters],
    queryFn: ({ pageParam, signal }) => getRecentUploads(filters, pageParam, signal),
    initialPageParam: 0,
    getNextPageParam: (lastPage: RecentUploadsPage, pages: RecentUploadsPage[]) =>
      lastPage.has_more
        ? pages.reduce((count: number, page: RecentUploadsPage) => count + page.images.length, 0)
        : undefined,
    retry: retryUnlessClientError,
  });
}

export interface ImageModeration {
  imageId: string;
  action: ImageModerationAction;
  reason: string;
}

async function moderateImage({ imageId, action, reason }: ImageModeration): Promise<void> {
  const options = { params: { path: { image_id: imageId } }, body: { reason } };
  switch (action) {
    case 'hide':
      throwIfError(await apiClient.POST('/moderation/images/{image_id}/hide', options));
      return;
    case 'unhide':
      throwIfError(await apiClient.POST('/moderation/images/{image_id}/unhide', options));
      return;
    case 'delete':
      throwIfError(await apiClient.POST('/moderation/images/{image_id}/delete', options));
      return;
  }
}

export function useModerateImage(): UseMutationResult<void, Error, ImageModeration> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: moderateImage,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: RECENT_UPLOADS_QUERY_KEY }),
        queryClient.invalidateQueries({ queryKey: MODERATION_LOG_QUERY_KEY }),
      ]);
    },
  });
}

async function searchAccounts(
  query: string | undefined,
  offset: number,
  signal: AbortSignal,
): Promise<AccountSearchPage> {
  return dataOrThrow(
    await apiClient.GET('/moderation/accounts', { params: { query: { query, offset } }, signal }),
  );
}

export function useAccountSearch(
  query: string | undefined,
): UseInfiniteQueryResult<InfiniteData<AccountSearchPage, number>> {
  return useInfiniteQuery({
    queryKey: [...ACCOUNT_SEARCH_QUERY_KEY, query],
    queryFn: ({ pageParam, signal }) => searchAccounts(query, pageParam, signal),
    initialPageParam: 0,
    getNextPageParam: (lastPage: AccountSearchPage, pages: AccountSearchPage[]) =>
      lastPage.has_more
        ? pages.reduce((count: number, page: AccountSearchPage) => count + page.accounts.length, 0)
        : undefined,
    retry: retryUnlessClientError,
  });
}

export function useAccount(accountId: string): UseQueryResult<Account> {
  return useQuery({
    queryKey: [...ACCOUNT_QUERY_KEY, accountId],
    queryFn: async ({ signal }) =>
      dataOrThrow(
        await apiClient.GET('/moderation/accounts/{user_id}', {
          params: { path: { user_id: accountId } },
          signal,
        }),
      ),
    retry: retryUnlessClientError,
  });
}

export interface TemplateModeration {
  templateId: string;
  action: TemplateModerationAction;
  reason: string;
}

async function moderateTemplate({ templateId, action, reason }: TemplateModeration): Promise<void> {
  const options = { params: { path: { template_id: templateId } }, body: { reason } };
  switch (action) {
    case 'hide':
      throwIfError(await apiClient.POST('/moderation/templates/{template_id}/hide', options));
      return;
    case 'unhide':
      throwIfError(await apiClient.POST('/moderation/templates/{template_id}/unhide', options));
      return;
    case 'delete':
      throwIfError(await apiClient.POST('/moderation/templates/{template_id}/delete', options));
      return;
  }
}

export function useModerateTemplate(): UseMutationResult<void, Error, TemplateModeration> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: moderateTemplate,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ACCOUNT_QUERY_KEY }),
        queryClient.invalidateQueries({ queryKey: MODERATION_LOG_QUERY_KEY }),
      ]);
    },
  });
}

export interface HideAllImages {
  accountId: string;
  reason: string;
}

export function useHideAllImages(): UseMutationResult<number, Error, HideAllImages> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ accountId, reason }: HideAllImages): Promise<number> => {
      const result = dataOrThrow(
        await apiClient.POST('/moderation/accounts/{user_id}/hide-images', {
          params: { path: { user_id: accountId } },
          body: { reason },
        }),
      );
      return result.hidden_count;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: RECENT_UPLOADS_QUERY_KEY }),
        queryClient.invalidateQueries({ queryKey: MODERATION_LOG_QUERY_KEY }),
      ]);
    },
  });
}

export interface AccountBanRequest {
  accountId: string;
  reason: string;
  endsAt?: string;
}

export function useBanAccount(): UseMutationResult<void, Error, AccountBanRequest> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ accountId, reason, endsAt }: AccountBanRequest): Promise<void> => {
      throwIfError(
        await apiClient.POST('/moderation/accounts/{user_id}/ban', {
          params: { path: { user_id: accountId } },
          body: { reason, ends_at: endsAt },
        }),
      );
    },
    onSuccess: () => invalidateAccount(queryClient),
  });
}

export function useLiftBan(): UseMutationResult<
  void,
  Error,
  { accountId: string; reason: string }
> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ accountId, reason }: { accountId: string; reason: string }) => {
      throwIfError(
        await apiClient.POST('/moderation/accounts/{user_id}/lift-ban', {
          params: { path: { user_id: accountId } },
          body: { reason },
        }),
      );
    },
    onSuccess: () => invalidateAccount(queryClient),
  });
}

async function invalidateAccount(queryClient: QueryClient): Promise<void> {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ACCOUNT_QUERY_KEY }),
    queryClient.invalidateQueries({ queryKey: ACCOUNT_SEARCH_QUERY_KEY }),
    queryClient.invalidateQueries({ queryKey: MODERATION_LOG_QUERY_KEY }),
  ]);
}
