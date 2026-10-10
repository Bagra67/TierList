import { type QueryClient, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { TEMPLATES_QUERY_KEY, templateQueryKey } from '../constants/templates';
import { apiClient, dataOrThrow, throwIfError } from './client';
import type { components } from './schema';

export type TemplateSummary = components['schemas']['TemplateSummaryResponse'];
export type Template = components['schemas']['TemplateResponse'];
type CreateTemplateRequest = components['schemas']['CreateTemplateRequest'];
export type Tier = Template['tiers'][number];
type TierChanges = components['schemas']['UpdateTierRequest'];

// Templates de l'utilisateur connecté, du plus récemment modifié au plus ancien (tri du backend)
async function listTemplates(signal?: AbortSignal): Promise<TemplateSummary[]> {
  const data = dataOrThrow(await apiClient.GET('/templates', { signal }));
  return data.items;
}

async function getTemplate(templateId: string, signal?: AbortSignal): Promise<Template> {
  return dataOrThrow(
    await apiClient.GET('/templates/{template_id}', {
      params: { path: { template_id: templateId } },
      signal,
    }),
  );
}

async function createTemplate(body: CreateTemplateRequest): Promise<Template> {
  return dataOrThrow(await apiClient.POST('/templates', { body }));
}

async function renameTemplate(templateId: string, name: string): Promise<Template> {
  return dataOrThrow(
    await apiClient.PATCH('/templates/{template_id}', {
      params: { path: { template_id: templateId } },
      body: { name },
    }),
  );
}

async function addTier(templateId: string): Promise<Template> {
  return dataOrThrow(
    await apiClient.POST('/templates/{template_id}/tiers', {
      params: { path: { template_id: templateId } },
    }),
  );
}

async function updateTier(
  templateId: string,
  tierId: string,
  changes: TierChanges,
): Promise<Template> {
  return dataOrThrow(
    await apiClient.PATCH('/templates/{template_id}/tiers/{tier_id}', {
      params: { path: { template_id: templateId, tier_id: tierId } },
      body: changes,
    }),
  );
}

async function deleteTier(templateId: string, tierId: string): Promise<Template> {
  return dataOrThrow(
    await apiClient.DELETE('/templates/{template_id}/tiers/{tier_id}', {
      params: { path: { template_id: templateId, tier_id: tierId } },
    }),
  );
}

async function deleteTemplate(templateId: string): Promise<void> {
  throwIfError(
    await apiClient.DELETE('/templates/{template_id}', {
      params: { path: { template_id: templateId } },
    }),
  );
}

export function useTemplates() {
  return useQuery({
    queryKey: TEMPLATES_QUERY_KEY,
    queryFn: ({ signal }) => listTemplates(signal),
  });
}

export function useTemplate(templateId: string) {
  return useQuery({
    queryKey: templateQueryKey(templateId),
    queryFn: ({ signal }) => getTemplate(templateId, signal),
  });
}

export function useCreateTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createTemplate,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: TEMPLATES_QUERY_KEY }),
  });
}

export function useDeleteTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteTemplate,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: TEMPLATES_QUERY_KEY }),
  });
}

// Les modifications d'un template renvoient le template à jour : il remplace celui du cache
// sans nouvelle lecture. La liste, elle, est relue (date de dernière modification changée).
function storeTemplate(queryClient: QueryClient, template: Template): Promise<void> {
  queryClient.setQueryData(templateQueryKey(template.id), template);
  return queryClient.invalidateQueries({ queryKey: TEMPLATES_QUERY_KEY, exact: true });
}

export function useRenameTemplate(templateId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => renameTemplate(templateId, name),
    onSuccess: (template) => storeTemplate(queryClient, template),
  });
}

export function useAddTier(templateId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => addTier(templateId),
    onSuccess: (template) => storeTemplate(queryClient, template),
  });
}

interface TierUpdate {
  tierId: string;
  changes: TierChanges;
}

// Tiers dans le nouvel ordre, avant la réponse du backend (qui applique la même règle)
function moveTier(tiers: Tier[], tierId: string, position: number): Tier[] {
  const reordered: Tier[] = tiers.filter((tier) => tier.id !== tierId);
  const movedTier = tiers.find((tier) => tier.id === tierId);
  if (movedTier === undefined) return tiers;
  reordered.splice(Math.min(position, reordered.length), 0, movedTier);
  return reordered.map((tier, index) => ({ ...tier, position: index }));
}

export function useUpdateTier(templateId: string) {
  const queryClient = useQueryClient();
  const queryKey = templateQueryKey(templateId);
  return useMutation({
    mutationFn: ({ tierId, changes }: TierUpdate) => updateTier(templateId, tierId, changes),
    // Déplacement optimiste : après un glisser-déposer, le tier reste où il a été déposé
    // pendant l'enregistrement, au lieu de revenir à sa place puis de sauter.
    onMutate: async ({ tierId, changes }: TierUpdate) => {
      if (changes.position === undefined || changes.position === null) return undefined;
      await queryClient.cancelQueries({ queryKey });
      const previous = queryClient.getQueryData<Template>(queryKey);
      if (previous !== undefined) {
        const tiers = moveTier(previous.tiers, tierId, changes.position);
        queryClient.setQueryData<Template>(queryKey, { ...previous, tiers });
      }
      return previous;
    },
    onError: (_error, _update, previous) => {
      if (previous !== undefined) queryClient.setQueryData(queryKey, previous);
    },
    onSuccess: (template) => storeTemplate(queryClient, template),
  });
}

export function useDeleteTier(templateId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tierId: string) => deleteTier(templateId, tierId),
    onSuccess: (template) => storeTemplate(queryClient, template),
  });
}
