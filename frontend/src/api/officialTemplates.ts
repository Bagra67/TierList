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
type OfficialTemplateLease = components['schemas']['OfficialTemplateLeaseResponse'];

const OFFICIAL_TEMPLATE_LOCKED: string = 'official_template_locked';

async function listOfficialTemplates(signal?: AbortSignal): Promise<OfficialTemplateSummary[]> {
  const data: OfficialTemplateList = dataOrThrow(
    await apiClient.GET('/moderation/official-templates', { signal }),
  );
  return data.items;
}

async function createOfficialTemplate(body: { name: string }): Promise<Template> {
  return dataOrThrow(await apiClient.POST('/moderation/official-templates', { body }));
}

async function lockOfficialTemplate(templateId: string): Promise<OfficialTemplateLease> {
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

const CHANGE_PATHS = {
  publish: '/moderation/official-templates/{template_id}/publish',
  unpublish: '/moderation/official-templates/{template_id}/unpublish',
  feature: '/moderation/official-templates/{template_id}/feature',
  unfeature: '/moderation/official-templates/{template_id}/unfeature',
} as const;

export type OfficialTemplateChange = keyof typeof CHANGE_PATHS;

async function changeOfficialTemplate(
  templateId: string,
  change: OfficialTemplateChange,
): Promise<Template> {
  return dataOrThrow(
    await apiClient.POST(CHANGE_PATHS[change], {
      params: { path: { template_id: templateId } },
    }),
  );
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

export function useCreateOfficialTemplate(): UseMutationResult<Template, Error, { name: string }> {
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

export type OfficialTemplateLockStatus = 'pending' | 'held' | 'taken';

export function useOfficialTemplateLock(
  templateId: string,
  enabled: boolean,
): OfficialTemplateLockStatus {
  const queryClient: QueryClient = useQueryClient();
  const [status, setStatus] = useState<OfficialTemplateLockStatus>('pending');

  useEffect(() => {
    if (!enabled) return undefined;
    let active: boolean = true;

    async function takeLease() {
      try {
        const lease: OfficialTemplateLease = await lockOfficialTemplate(templateId);
        if (!active) return;
        queryClient.setQueryData<Template>(templateQueryKey(templateId), (current) =>
          current === undefined ? current : { ...current, ...lease },
        );
        setStatus('held');
      } catch (error) {
        if (!active || !(error instanceof ApiError) || error.code !== OFFICIAL_TEMPLATE_LOCKED) {
          return;
        }
        setStatus('taken');
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

  return status;
}
