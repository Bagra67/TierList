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

// Déplacement d'un tier, connu avant la réponse du backend
interface PendingMove {
  itemId: string;
  position: number;
}

interface Positioned {
  id: string;
  position: number;
}

// Éléments dans le nouvel ordre, avant la réponse du backend (qui applique la même règle)
function moveItem<Item extends Positioned>(
  items: Item[],
  itemId: string,
  position: number,
): Item[] {
  const movedItem: Item | undefined = items.find((item) => item.id === itemId);
  if (movedItem === undefined) return items;
  const reordered: Item[] = items.filter((item) => item.id !== itemId);
  reordered.splice(Math.min(position, reordered.length), 0, movedItem);
  return reordered.map((item, index) => ({ ...item, position: index }));
}

// Mutation qui modifie un template ouvert dans l'éditeur et renvoie le template à jour. Tout ce
// qui est commun à ces modifications est écrit ici une seule fois : le template renvoyé remplace
// celui du cache et, quand getMove décrit un déplacement, celui-ci est affiché tout de suite
// (après un glisser-déposer, l'élément reste où il a été déposé au lieu de revenir puis sauter),
// puis annulé si l'enregistrement échoue.
function useTemplateChange<Variables = void>(
  templateId: string,
  mutationFn: (variables: Variables) => Promise<Template>,
  getMove?: (variables: Variables) => PendingMove | undefined,
) {
  const queryClient = useQueryClient();
  const queryKey = templateQueryKey(templateId);
  return useMutation({
    mutationFn,
    onMutate: async (variables: Variables): Promise<Template | undefined> => {
      const move: PendingMove | undefined = getMove?.(variables);
      if (move === undefined) return undefined;
      await queryClient.cancelQueries({ queryKey });
      const previous: Template | undefined = queryClient.getQueryData<Template>(queryKey);
      if (previous !== undefined) {
        const tiers: Tier[] = moveItem(previous.tiers, move.itemId, move.position);
        queryClient.setQueryData<Template>(queryKey, { ...previous, tiers });
      }
      return previous;
    },
    onError: (_error, _variables, previous) => {
      if (previous !== undefined) queryClient.setQueryData(queryKey, previous);
    },
    onSuccess: (template) => storeTemplate(queryClient, template),
  });
}

export function useRenameTemplate(templateId: string) {
  return useTemplateChange(templateId, (name: string) => renameTemplate(templateId, name));
}

export function useAddTier(templateId: string) {
  return useTemplateChange(templateId, () => addTier(templateId));
}

interface TierUpdate {
  tierId: string;
  changes: TierChanges;
}

export function useUpdateTier(templateId: string) {
  return useTemplateChange(
    templateId,
    ({ tierId, changes }: TierUpdate) => updateTier(templateId, tierId, changes),
    ({ tierId, changes }: TierUpdate) =>
      changes.position === undefined || changes.position === null
        ? undefined
        : { itemId: tierId, position: changes.position },
  );
}

export function useDeleteTier(templateId: string) {
  return useTemplateChange(templateId, (tierId: string) => deleteTier(templateId, tierId));
}
