import {
  type QueryClient,
  useMutation,
  type UseMutationResult,
  useQuery,
  useQueryClient,
  type UseQueryResult,
} from '@tanstack/react-query';

import { isTemplateId, publicTemplateQueryKey } from '../constants/templates';
import { apiClient, dataOrThrow } from './client';
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
