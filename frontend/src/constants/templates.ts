// Doit rester égale à la limite du backend (backend/app/constants/templates.py), liée au schéma
// de la base
export const TEMPLATE_NAME_MAX_LENGTH = 100;

// Entrées du cache TanStack Query : la liste et chaque template partagent ce préfixe, une
// seule invalidation les rafraîchit tous
export const TEMPLATES_QUERY_KEY = ['templates'] as const;

export function templateQueryKey(templateId: string) {
  return [...TEMPLATES_QUERY_KEY, templateId] as const;
}
