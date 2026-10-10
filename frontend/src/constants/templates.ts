// Doivent rester égales aux limites du backend (backend/app/constants/templates.py), liées au
// schéma de la base
export const TEMPLATE_NAME_MAX_LENGTH: number = 100;
export const TIER_NAME_MAX_LENGTH: number = 50;

// TanStack Query garde en cache chaque donnée lue sur l'API, rangée sous une « clé » (un
// tableau). Les clés des templates commencent toutes par 'templates' :
// - la liste de « Mes templates » : ['templates']
// - un template ouvert dans l'éditeur : ['templates', <id>]
// Après une création ou une suppression, invalider le préfixe ['templates'] fait relire
// d'un coup la liste et les templates déjà ouverts : l'interface ne montre pas de données périmées.
export const TEMPLATES_QUERY_KEY: readonly ['templates'] = ['templates'];

export type TemplateQueryKey = readonly ['templates', string];

export function templateQueryKey(templateId: string): TemplateQueryKey {
  return [...TEMPLATES_QUERY_KEY, templateId];
}
