import {
  type QueryClient,
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';

import {
  TEMPLATES_QUERY_KEY,
  type TemplateQueryKey,
  templateQueryKey,
} from '../constants/templates';
import { apiClient, dataOrThrow, throwIfError } from './client';
import type { components } from './schema';

export type TemplateSummary = components['schemas']['TemplateSummaryResponse'];
export type Template = components['schemas']['TemplateResponse'];
type TemplateList = components['schemas']['TemplateListResponse'];
type CreateTemplateRequest = components['schemas']['CreateTemplateRequest'];
export type Tier = Template['tiers'][number];
type TierChanges = components['schemas']['UpdateTierRequest'];
export type Tile = Template['tiles'][number];
// Un texte, une image envoyée avant (image_id), ou les deux
export type NewTile = components['schemas']['CreateTileRequest'];
type TileChanges = components['schemas']['UpdateTileRequest'];

// Templates de l'utilisateur connecté, du plus récemment modifié au plus ancien (tri du backend)
async function listTemplates(signal?: AbortSignal): Promise<TemplateSummary[]> {
  const data: TemplateList = dataOrThrow(await apiClient.GET('/templates', { signal }));
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
    queryKey: TEMPLATES_QUERY_KEY,
    queryFn: ({ signal }) => listTemplates(signal),
  });
}

export function useTemplate(templateId: string): UseQueryResult<Template> {
  return useQuery({
    queryKey: templateQueryKey(templateId),
    queryFn: ({ signal }) => getTemplate(templateId, signal),
  });
}

export function useCreateTemplate(): UseMutationResult<Template, Error, CreateTemplateRequest> {
  const queryClient: QueryClient = useQueryClient();
  return useMutation({
    mutationFn: createTemplate,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: TEMPLATES_QUERY_KEY }),
  });
}

export function useDeleteTemplate(): UseMutationResult<void, Error, string> {
  const queryClient: QueryClient = useQueryClient();
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

// Modification d'un template ouvert : renvoie le template à jour ; le contexte est le template
// d'avant un déplacement, rétabli si l'enregistrement échoue
export type TemplateChange<Variables> = UseMutationResult<
  Template,
  Error,
  Variables,
  Template | undefined
>;

// Déplacement d'un tier ou d'une tuile, connu avant la réponse du backend
interface PendingMove {
  list: 'tiers' | 'tiles';
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

function applyMove(template: Template, move: PendingMove): Template {
  if (move.list === 'tiers') {
    return { ...template, tiers: moveItem(template.tiers, move.itemId, move.position) };
  }
  return { ...template, tiles: moveItem(template.tiles, move.itemId, move.position) };
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
): TemplateChange<Variables> {
  const queryClient: QueryClient = useQueryClient();
  const queryKey: TemplateQueryKey = templateQueryKey(templateId);
  return useMutation({
    mutationFn,
    onMutate: async (variables: Variables): Promise<Template | undefined> => {
      const move: PendingMove | undefined = getMove?.(variables);
      if (move === undefined) return undefined;
      await queryClient.cancelQueries({ queryKey });
      const previous: Template | undefined = queryClient.getQueryData<Template>(queryKey);
      if (previous !== undefined) {
        queryClient.setQueryData<Template>(queryKey, applyMove(previous, move));
      }
      return previous;
    },
    onError: (_error, _variables, previous) => {
      if (previous !== undefined) queryClient.setQueryData(queryKey, previous);
    },
    onSuccess: (template) => storeTemplate(queryClient, template),
  });
}

export function useRenameTemplate(templateId: string): TemplateChange<string> {
  return useTemplateChange(templateId, (name: string) => renameTemplate(templateId, name));
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
    ({ tierId, changes }: TierUpdate) =>
      changes.position === undefined || changes.position === null
        ? undefined
        : { list: 'tiers', itemId: tierId, position: changes.position },
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
    ({ tileId, changes }: TileUpdate) =>
      changes.position === undefined || changes.position === null
        ? undefined
        : { list: 'tiles', itemId: tileId, position: changes.position },
  );
}

export function useDeleteTile(templateId: string): TemplateChange<string> {
  return useTemplateChange(templateId, (tileId: string) => deleteTile(templateId, tileId));
}
