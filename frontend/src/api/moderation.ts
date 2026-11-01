import {
  type InfiniteData,
  type UseInfiniteQueryResult,
  type UseQueryResult,
  type UseMutationResult,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';

import { apiClient, dataOrThrow, throwIfError } from './client';
import { retryUnlessClientError } from './queryClient';
import type { components } from './schema';

export type ModerationLogPage = components['schemas']['ModerationLogResponse'];
export type ModerationLogEntry = components['schemas']['ModerationActionResponse'];
export type SuperAdmin = components['schemas']['SuperAdminResponse'];
export type RecentUploadsPage = components['schemas']['RecentUploadsResponse'];
export type RecentUpload = components['schemas']['RecentUploadResponse'];
// Statuts listés par les derniers envois : une image supprimée n'a plus de fichier
export type ListedImageStatus = 'visible' | 'hidden';
export type ImageModerationAction = 'hide' | 'unhide' | 'delete';

// Filtres du journal : un super admin (son id) et un texte cherché dans le libellé de la cible
export interface ModerationLogFilters {
  actorId?: string;
  target?: string;
}

const MODERATION_LOG_QUERY_KEY = ['moderation', 'log'] as const;
const SUPER_ADMINS_QUERY_KEY = ['moderation', 'super-admins'] as const;
const RECENT_UPLOADS_QUERY_KEY = ['moderation', 'images'] as const;

// Filtres des derniers envois : un texte cherché dans le nom ou l'e-mail de l'auteur, une période
// d'envoi (dates ISO avec fuseau : début inclus, fin exclue) et un statut
export interface RecentUploadsFilters {
  author?: string;
  createdAfter?: string;
  createdBefore?: string;
  status?: ListedImageStatus;
}

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

// Une page des derniers envois à partir de offset (US-1.7)
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
        },
      },
      signal,
    }),
  );
}

// Les derniers envois page par page, pour ces filtres : « Voir plus » lit la page suivante tant
// que le backend en annonce. Changer de filtre repart de la première page (autre clé de requête)
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

// Masque, réaffiche ou supprime une image (US-1.4), avec le motif écrit au journal
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

// Une action de modération sur une image : les derniers envois et le journal sont relus
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
