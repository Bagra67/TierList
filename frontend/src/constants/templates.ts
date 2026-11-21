export const TEMPLATE_NAME_MAX_LENGTH: number = 100;
export const TIER_NAME_MAX_LENGTH: number = 50;
export const TILE_TEXT_MAX_LENGTH: number = 200;
export const TAG_MAX_LENGTH: number = 30;

export const TIER_COLOR_PRESETS: readonly string[] = [
  '#FF3B6B',
  '#FF8A2A',
  '#FFC22E',
  '#7BD94A',
  '#2EC4B6',
  '#5B7CFA',
  '#4FC3F7',
  '#A78BFA',
  '#F06BD0',
  '#D4B483',
  '#3D405B',
  '#9AA0B4',
];

const TEMPLATE_ID_PATTERN: RegExp =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function isTemplateId(value: string): boolean {
  return TEMPLATE_ID_PATTERN.test(value);
}

export const TEMPLATE_LIST_QUERY_KEY: readonly ['templates', 'list'] = ['templates', 'list'];

export const OFFICIAL_TEMPLATES_QUERY_KEY: readonly ['templates', 'official'] = [
  'templates',
  'official',
];
export const OFFICIAL_TEMPLATE_LOCK_RENEW_MS: number = 30_000;

export const REMOVED_TEMPLATES_QUERY_KEY: readonly ['templates', 'removed'] = [
  'templates',
  'removed',
];

export type TemplateQueryKey = readonly ['templates', 'detail', string];

export function templateQueryKey(templateId: string): TemplateQueryKey {
  return ['templates', 'detail', templateId];
}

export const MARKETPLACE_LIST_QUERY_KEY: readonly ['marketplace', 'list'] = ['marketplace', 'list'];
export const MARKETPLACE_TAGS_QUERY_KEY: readonly ['marketplace', 'tags'] = ['marketplace', 'tags'];
export const CARD_STATES_STALE_MS: number = 60_000;
export const MARKETPLACE_LIKE_STATES_QUERY_KEY: readonly ['marketplace', 'likes'] = [
  'marketplace',
  'likes',
];
export const MARKETPLACE_FAVORITE_STATES_QUERY_KEY: readonly ['marketplace', 'favorite-states'] = [
  'marketplace',
  'favorite-states',
];
export const FAVORITE_TEMPLATES_QUERY_KEY: readonly ['marketplace', 'favorites'] = [
  'marketplace',
  'favorites',
];

export function publicTemplateQueryKey(templateId: string): readonly string[] {
  return ['marketplace', 'templates', templateId];
}

export function templateChangeMutationKey(templateId: string): readonly string[] {
  return [...templateQueryKey(templateId), 'change'];
}
