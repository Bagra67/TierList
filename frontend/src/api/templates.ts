import {
  type QueryClient,
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';

import {
  isTemplateId,
  REMOVED_TEMPLATES_QUERY_KEY,
  TEMPLATE_LIST_QUERY_KEY,
  templateChangeMutationKey,
  type TemplateQueryKey,
  templateQueryKey,
} from '../constants/templates';
import { apiClient, dataOrThrow, throwIfError } from './client';
import { retryUnlessClientError } from './queryClient';
import type { components } from './schema';

export type TemplateSummary = components['schemas']['TemplateSummaryResponse'];
export type Template = components['schemas']['TemplateResponse'];
type TemplateList = components['schemas']['TemplateListResponse'];
export type RemovedTemplate = components['schemas']['RemovedTemplateResponse'];
type RemovedTemplateList = components['schemas']['RemovedTemplateListResponse'];
type CreateTemplateRequest = components['schemas']['CreateTemplateRequest'];
export type Tier = Template['tiers'][number];
type TierChanges = components['schemas']['UpdateTierRequest'];
export type Tile = Template['tiles'][number];
export type NewTile = components['schemas']['CreateTileRequest'];
type TileChanges = components['schemas']['UpdateTileRequest'];
export type TemplateVisibility = components['schemas']['TemplateVisibility'];

async function listTemplates(signal?: AbortSignal): Promise<TemplateSummary[]> {
  const data: TemplateList = dataOrThrow(await apiClient.GET('/templates', { signal }));
  return data.items;
}

async function listRemovedTemplates(signal?: AbortSignal): Promise<RemovedTemplate[]> {
  const data: RemovedTemplateList = dataOrThrow(
    await apiClient.GET('/templates/removed', { signal }),
  );
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

async function setTemplateTags(templateId: string, tags: string[]): Promise<Template> {
  return dataOrThrow(
    await apiClient.PUT('/templates/{template_id}/tags', {
      params: { path: { template_id: templateId } },
      body: { tags },
    }),
  );
}

async function setTemplateVisibility(
  templateId: string,
  visibility: TemplateVisibility,
): Promise<Template> {
  return dataOrThrow(
    await apiClient.PUT('/templates/{template_id}/visibility', {
      params: { path: { template_id: templateId } },
      body: { visibility },
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

async function addTile(templateId: string, newTile: NewTile): Promise<Template> {
  return dataOrThrow(
    await apiClient.POST('/templates/{template_id}/tiles', {
      params: { path: { template_id: templateId } },
      body: newTile,
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

export function useTemplates(): UseQueryResult<TemplateSummary[]> {
  return useQuery({
    queryKey: TEMPLATE_LIST_QUERY_KEY,
    queryFn: ({ signal }) => listTemplates(signal),
    retry: retryUnlessClientError,
  });
}

export function useRemovedTemplates(): UseQueryResult<RemovedTemplate[]> {
  return useQuery({
    queryKey: REMOVED_TEMPLATES_QUERY_KEY,
    queryFn: ({ signal }) => listRemovedTemplates(signal),
    retry: retryUnlessClientError,
  });
}

export function useTemplate(templateId: string): UseQueryResult<Template> {
  return useQuery({
    queryKey: templateQueryKey(templateId),
    queryFn: ({ signal }) => getTemplate(templateId, signal),
    enabled: isTemplateId(templateId),
    retry: retryUnlessClientError,
  });
}

export function useCreateTemplate(): UseMutationResult<Template, Error, CreateTemplateRequest> {
  const queryClient: QueryClient = useQueryClient();
  return useMutation({
    mutationFn: createTemplate,
    onSuccess: (template: Template) => storeTemplate(queryClient, template),
  });
}

export function useDeleteTemplate(): UseMutationResult<void, Error, string> {
  const queryClient: QueryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteTemplate,
    onSuccess: async (_nothing: void, templateId: string) => {
      queryClient.removeQueries({ queryKey: templateQueryKey(templateId) });
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: TEMPLATE_LIST_QUERY_KEY }),
        queryClient.invalidateQueries({ queryKey: REMOVED_TEMPLATES_QUERY_KEY }),
      ]);
    },
  });
}

function storeTemplate(queryClient: QueryClient, template: Template): Promise<void> {
  queryClient.setQueryData(templateQueryKey(template.id), template);
  return queryClient.invalidateQueries({ queryKey: TEMPLATE_LIST_QUERY_KEY });
}

export type TemplateChange<Variables> = UseMutationResult<
  Template,
  Error,
  Variables,
  Template | undefined
>;

interface PendingMove {
  list: 'tiers' | 'tiles';
  itemId: string;
  position: number;
}

interface Positioned {
  id: string;
  position: number;
}

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

function applyMove(template: Template, move: PendingMove): Template {
  if (move.list === 'tiers') {
    return { ...template, tiers: moveItem(template.tiers, move.itemId, move.position) };
  }
  return { ...template, tiles: moveItem(template.tiles, move.itemId, move.position) };
}

type OptimisticUpdate = (template: Template) => Template;

function positionUpdate(
  list: PendingMove['list'],
  itemId: string,
  position: number | null | undefined,
): OptimisticUpdate | undefined {
  if (position === undefined || position === null) return undefined;
  return (template: Template) => applyMove(template, { list, itemId, position });
}

function useTemplateChange<Variables = void>(
  templateId: string,
  mutationFn: (variables: Variables) => Promise<Template>,
  getOptimisticUpdate?: (variables: Variables) => OptimisticUpdate | undefined,
): TemplateChange<Variables> {
  const queryClient: QueryClient = useQueryClient();
  const queryKey: TemplateQueryKey = templateQueryKey(templateId);
  return useMutation({
    mutationKey: templateChangeMutationKey(templateId),
    mutationFn,
    onMutate: async (variables: Variables): Promise<Template | undefined> => {
      const optimisticUpdate: OptimisticUpdate | undefined = getOptimisticUpdate?.(variables);
      if (optimisticUpdate === undefined) return undefined;
      await queryClient.cancelQueries({ queryKey });
      const previous: Template | undefined = queryClient.getQueryData<Template>(queryKey);
      if (previous !== undefined) {
        queryClient.setQueryData<Template>(queryKey, optimisticUpdate(previous));
      }
      return previous;
    },
    onSettled: async (template, _error, _variables, previous) => {
      const otherChangesPending: boolean =
        queryClient.isMutating({ mutationKey: templateChangeMutationKey(templateId) }) > 1;
      if (otherChangesPending) return;
      if (template !== undefined) {
        await storeTemplate(queryClient, template);
        return;
      }
      if (previous !== undefined) queryClient.setQueryData(queryKey, previous);
      await queryClient.invalidateQueries({ queryKey });
    },
  });
}

export function useRenameTemplate(templateId: string): TemplateChange<string> {
  return useTemplateChange(templateId, (name: string) => renameTemplate(templateId, name));
}

export function useSetTemplateVisibility(templateId: string): TemplateChange<TemplateVisibility> {
  return useTemplateChange(
    templateId,
    (visibility: TemplateVisibility) => setTemplateVisibility(templateId, visibility),
    (visibility: TemplateVisibility) => (template: Template) => ({ ...template, visibility }),
  );
}

export function useSetTemplateTags(templateId: string): TemplateChange<string[]> {
  return useTemplateChange(templateId, (tags: string[]) => setTemplateTags(templateId, tags));
}

export function useAddTier(templateId: string): TemplateChange<void> {
  return useTemplateChange(templateId, () => addTier(templateId));
}

export interface TierUpdate {
  tierId: string;
  changes: TierChanges;
}

export function useUpdateTier(templateId: string): TemplateChange<TierUpdate> {
  return useTemplateChange(
    templateId,
    ({ tierId, changes }: TierUpdate) => updateTier(templateId, tierId, changes),
    ({ tierId, changes }: TierUpdate) => positionUpdate('tiers', tierId, changes.position),
  );
}

export function useDeleteTier(templateId: string): TemplateChange<string> {
  return useTemplateChange(templateId, (tierId: string) => deleteTier(templateId, tierId));
}

export function useAddTile(templateId: string): TemplateChange<NewTile> {
  return useTemplateChange(templateId, (newTile: NewTile) => addTile(templateId, newTile));
}

export interface TileUpdate {
  tileId: string;
  changes: TileChanges;
}

export function useUpdateTile(templateId: string): TemplateChange<TileUpdate> {
  return useTemplateChange(
    templateId,
    ({ tileId, changes }: TileUpdate) => updateTile(templateId, tileId, changes),
    ({ tileId, changes }: TileUpdate) => positionUpdate('tiles', tileId, changes.position),
  );
}

export function useDeleteTile(templateId: string): TemplateChange<string> {
  return useTemplateChange(templateId, (tileId: string) => deleteTile(templateId, tileId));
}
