export const TEMPLATE_NAME_MAX_LENGTH: number = 100;
export const TIER_NAME_MAX_LENGTH: number = 50;
export const TILE_TEXT_MAX_LENGTH: number = 200;
export const TAG_MAX_LENGTH: number = 30;
export const TEMPLATE_MAX_TAGS: number = 5;

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

export const REMOVED_TEMPLATES_QUERY_KEY: readonly ['templates', 'removed'] = [
  'templates',
  'removed',
];

export type TemplateQueryKey = readonly ['templates', 'detail', string];

export function templateQueryKey(templateId: string): TemplateQueryKey {
  return ['templates', 'detail', templateId];
}

export function templateChangeMutationKey(templateId: string): readonly string[] {
  return [...templateQueryKey(templateId), 'change'];
}
