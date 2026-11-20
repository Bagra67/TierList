import {
  type QueryClient,
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import { useEffect, useState } from 'react';

import {
  OFFICIAL_TEMPLATE_LOCK_RENEW_MS,
  OFFICIAL_TEMPLATES_QUERY_KEY,
  templateQueryKey,
} from '../constants/templates';
import { ApiError } from '../errors/apiError';
import { apiClient, dataOrThrow, throwIfError } from './client';
import { retryUnlessClientError } from './queryClient';
import type { components } from './schema';
import type { Template } from './templates';

export type OfficialTemplateSummary = components['schemas']['OfficialTemplateSummaryResponse'];
type OfficialTemplateList = components['schemas']['OfficialTemplateListResponse'];
export type OfficialTemplateChange = 'publish' | 'unpublish' | 'feature' | 'unfeature';

const OFFICIAL_TEMPLATE_LOCKED: string = 'official_template_locked';

async function listOfficialTemplates(signal?: AbortSignal): Promise<OfficialTemplateSummary[]> {
  const data: OfficialTemplateList = dataOrThrow(
    await apiClient.GET('/moderation/official-templates', { signal }),
  );
  return data.items;
}

async function createOfficialTemplate(name: string): Promise<Template> {
  return dataOrThrow(await apiClient.POST('/moderation/official-templates', { body: { name } }));
}

async function lockOfficialTemplate(templateId: string): Promise<Template> {
  return dataOrThrow(
    await apiClient.POST('/moderation/official-templates/{template_id}/lock', {
      params: { path: { template_id: templateId } },
    }),
  );
}

async function unlockOfficialTemplate(templateId: string): Promise<void> {
  throwIfError(
    await apiClient.DELETE('/moderation/official-templates/{template_id}/lock', {
      params: { path: { template_id: templateId } },
      keepalive: true,
    }),
  );
}

async function changeOfficialTemplate(
  templateId: string,
  change: OfficialTemplateChange,
): Promise<Template> {
  const params = { params: { path: { template_id: templateId } } };
  switch (change) {
    case 'publish':
      return dataOrThrow(
        await apiClient.POST('/moderation/official-templates/{template_id}/publish', params),
      );
    case 'unpublish':
      return dataOrThrow(
        await apiClient.POST('/moderation/official-templates/{template_id}/unpublish', params),
      );
    case 'feature':
      return dataOrThrow(
        await apiClient.POST('/moderation/official-templates/{template_id}/feature', params),
      );
    case 'unfeature':
      return dataOrThrow(
        await apiClient.POST('/moderation/official-templates/{template_id}/unfeature', params),
      );
  }
}

async function deleteOfficialTemplate(templateId: string): Promise<void> {
  throwIfError(
    await apiClient.DELETE('/moderation/official-templates/{template_id}', {
      params: { path: { template_id: templateId } },
    }),
  );
}

export function useOfficialTemplates(): UseQueryResult<OfficialTemplateSummary[]> {
  return useQuery({
    queryKey: OFFICIAL_TEMPLATES_QUERY_KEY,
    queryFn: ({ signal }) => listOfficialTemplates(signal),
    retry: retryUnlessClientError,
  });
}

function storeOfficialTemplate(queryClient: QueryClient, template: Template): Promise<void> {
  queryClient.setQueryData(templateQueryKey(template.id), template);
  return queryClient.invalidateQueries({ queryKey: OFFICIAL_TEMPLATES_QUERY_KEY });
}

export function useCreateOfficialTemplate(): UseMutationResult<Template, Error, string> {
  const queryClient: QueryClient = useQueryClient();
  return useMutation({
    mutationFn: createOfficialTemplate,
    onSuccess: (template: Template) => storeOfficialTemplate(queryClient, template),
  });
}

export function useChangeOfficialTemplate(
  templateId: string,
): UseMutationResult<Template, Error, OfficialTemplateChange> {
  const queryClient: QueryClient = useQueryClient();
  return useMutation({
    mutationFn: (change: OfficialTemplateChange) => changeOfficialTemplate(templateId, change),
    onSuccess: (template: Template) => storeOfficialTemplate(queryClient, template),
  });
}

export function useDeleteOfficialTemplate(templateId: string): UseMutationResult<void, Error> {
  const queryClient: QueryClient = useQueryClient();
  return useMutation({
    mutationFn: () => deleteOfficialTemplate(templateId),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: templateQueryKey(templateId) });
      return queryClient.invalidateQueries({ queryKey: OFFICIAL_TEMPLATES_QUERY_KEY });
    },
  });
}

export type OfficialTemplateLock =
  { status: 'pending' } | { status: 'held' } | { status: 'taken'; editorName: string | null };

export function useOfficialTemplateLock(
  templateId: string,
  enabled: boolean,
): OfficialTemplateLock {
  const queryClient: QueryClient = useQueryClient();
  const [lock, setLock] = useState<OfficialTemplateLock>({ status: 'pending' });

  useEffect(() => {
    if (!enabled) return undefined;
    let active: boolean = true;

    async function takeLease() {
      try {
        const template: Template = await lockOfficialTemplate(templateId);
        if (!active) return;
        queryClient.setQueryData<Template>(templateQueryKey(templateId), (current) =>
          current === undefined
            ? template
            : {
                ...current,
                editing_by_name: template.editing_by_name,
                editing_until: template.editing_until,
              },
        );
        setLock({ status: 'held' });
      } catch (error) {
        if (!active || !(error instanceof ApiError) || error.code !== OFFICIAL_TEMPLATE_LOCKED) {
          return;
        }
        const editor: unknown = error.params?.editor;
        setLock({ status: 'taken', editorName: typeof editor === 'string' ? editor : null });
        await queryClient.invalidateQueries({ queryKey: templateQueryKey(templateId) });
      }
    }

    function giveBackLease() {
      void unlockOfficialTemplate(templateId).catch(() => undefined);
    }

    function renewWhileVisible() {
      if (document.visibilityState === 'visible') void takeLease();
    }

    void takeLease();
    const timer: number = window.setInterval(renewWhileVisible, OFFICIAL_TEMPLATE_LOCK_RENEW_MS);
    document.addEventListener('visibilitychange', renewWhileVisible);
    window.addEventListener('pagehide', giveBackLease);
    return () => {
      active = false;
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', renewWhileVisible);
      window.removeEventListener('pagehide', giveBackLease);
      giveBackLease();
    };
  }, [enabled, queryClient, templateId]);

  return lock;
}
