import { useQuery, type UseQueryResult } from '@tanstack/react-query';

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
