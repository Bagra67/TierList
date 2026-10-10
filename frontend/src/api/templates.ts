import { type QueryClient, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { TEMPLATES_QUERY_KEY, templateQueryKey } from '../constants/templates';
import { apiClient, dataOrThrow, throwIfError } from './client';
import type { components } from './schema';

export type TemplateSummary = components['schemas']['TemplateSummaryResponse'];
export type Template = components['schemas']['TemplateResponse'];
type CreateTemplateRequest = components['schemas']['CreateTemplateRequest'];
export type Tier = Template['tiers'][number];
type TierChanges = components['schemas']['UpdateTierRequest'];
export type Tile = Template['tiles'][number];
type TileChanges = components['schemas']['UpdateTileRequest'];

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

async function addTile(templateId: string, text: string): Promise<Template> {
  return dataOrThrow(
    await apiClient.POST('/templates/{template_id}/tiles', {
      params: { path: { template_id: templateId } },
      body: { text },
    }),
  );
}

async function updateTile(
  templateId: string,
  tileId: string,
  changes: TileChanges,
): Promise<Template> {
  return dataOrThrow(
    await apiClient.PATCH('/templates/{template_id}/tiles/{tile_id}', {
      params: { path: { template_id: templateId, tile_id: tileId } },
      body: changes,
    }),
  );
}

async function deleteTile(templateId: string, tileId: string): Promise<Template> {
  return dataOrThrow(
    await apiClient.DELETE('/templates/{template_id}/tiles/{tile_id}', {
      params: { path: { template_id: templateId, tile_id: tileId } },
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
  const movedItem = items.find((item) => item.id === itemId);
  if (movedItem === undefined) return items;
  const reordered: Item[] = items.filter((item) => item.id !== itemId);
  reordered.splice(Math.min(position, reordered.length), 0, movedItem);
  return reordered.map((item, index) => ({ ...item, position: index }));
}

// Déplacement optimiste : après un glisser-déposer, l'élément reste où il a été déposé
// pendant l'enregistrement, au lieu de revenir à sa place puis de sauter. Renvoie le
// template d'avant, rétabli si l'enregistrement échoue.
async function applyMove(
  queryClient: QueryClient,
  templateId: string,
  list: 'tiers' | 'tiles',
  itemId: string,
  position: number | null | undefined,
): Promise<Template | undefined> {
  if (position === undefined || position === null) return undefined;
  const queryKey = templateQueryKey(templateId);
  await queryClient.cancelQueries({ queryKey });
  const previous = queryClient.getQueryData<Template>(queryKey);
  if (previous !== undefined) {
    const moved: Template =
      list === 'tiers'
        ? { ...previous, tiers: moveItem(previous.tiers, itemId, position) }
        : { ...previous, tiles: moveItem(previous.tiles, itemId, position) };
    queryClient.setQueryData<Template>(queryKey, moved);
  }
  return previous;
}

function restoreTemplate(queryClient: QueryClient, previous: Template | undefined): void {
  if (previous !== undefined) queryClient.setQueryData(templateQueryKey(previous.id), previous);
}

interface TierUpdate {
  tierId: string;
  changes: TierChanges;
}

export function useUpdateTier(templateId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ tierId, changes }: TierUpdate) => updateTier(templateId, tierId, changes),
    onMutate: ({ tierId, changes }: TierUpdate) =>
      applyMove(queryClient, templateId, 'tiers', tierId, changes.position),
    onError: (_error, _update, previous) => restoreTemplate(queryClient, previous),
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

export function useAddTile(templateId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (text: string) => addTile(templateId, text),
    onSuccess: (template) => storeTemplate(queryClient, template),
  });
}

interface TileUpdate {
  tileId: string;
  changes: TileChanges;
}

export function useUpdateTile(templateId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ tileId, changes }: TileUpdate) => updateTile(templateId, tileId, changes),
    onMutate: ({ tileId, changes }: TileUpdate) =>
      applyMove(queryClient, templateId, 'tiles', tileId, changes.position),
    onError: (_error, _update, previous) => restoreTemplate(queryClient, previous),
    onSuccess: (template) => storeTemplate(queryClient, template),
  });
}

export function useDeleteTile(templateId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tileId: string) => deleteTile(templateId, tileId),
    onSuccess: (template) => storeTemplate(queryClient, template),
  });
}
