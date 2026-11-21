import { generatePath } from 'react-router';

export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  VERIFY_EMAIL: '/verify-email',
  FORGOT_PASSWORD: '/forgot-password',
  RESET_PASSWORD: '/reset-password',
  TEMPLATES: '/templates',
  TEMPLATE_EDITOR: '/templates/:templateId',
  MARKETPLACE: '/marketplace',
  PUBLIC_TEMPLATE: '/marketplace/templates/:templateId',
  FAVORITES: '/favorites',
  HISTORY: '/history',
  MODERATION: '/moderation',
  MODERATION_REPORTS: '/moderation/reports',
  MODERATION_UPLOADS: '/moderation/uploads',
  MODERATION_ACCOUNTS: '/moderation/accounts',
  MODERATION_ACCOUNT: '/moderation/accounts/:accountId',
  MODERATION_TEMPLATE: '/moderation/templates/:templateId',
  MODERATION_DELETED_TEMPLATES: '/moderation/deleted-templates',
  MODERATION_OFFICIAL_TEMPLATES: '/moderation/official-templates',
  MODERATION_OFFICIAL_TEMPLATE: '/moderation/official-templates/:templateId',
  MODERATION_LOG: '/moderation/log',
  ROOM: '/r/:code',
  RESULTS: '/results/:token',
  PRIVACY: '/privacy',
  TERMS: '/terms',
  LEGAL_NOTICE: '/legal',
} as const;

export function templateEditorPath(templateId: string): string {
  return generatePath(ROUTES.TEMPLATE_EDITOR, { templateId });
}

export function publicTemplatePath(templateId: string): string {
  return generatePath(ROUTES.PUBLIC_TEMPLATE, { templateId });
}

export const MARKETPLACE_SEARCH_PARAM = 'q';
export const MARKETPLACE_TAG_PARAM = 'tag';
export const MARKETPLACE_SORT_PARAM = 'sort';

export function marketplaceTagPath(tag: string): string {
  return `${ROUTES.MARKETPLACE}?${new URLSearchParams({ [MARKETPLACE_TAG_PARAM]: tag }).toString()}`;
}

export function roomPath(code: string): string {
  return generatePath(ROUTES.ROOM, { code });
}

export function resultsPath(token: string): string {
  return generatePath(ROUTES.RESULTS, { token });
}

export interface ResultsLinkState {
  roomCode: string;
  isAdmin: boolean;
}

export function isResultsLinkState(state: unknown): state is ResultsLinkState {
  return (
    typeof state === 'object' &&
    state !== null &&
    'roomCode' in state &&
    typeof state.roomCode === 'string' &&
    'isAdmin' in state &&
    typeof state.isAdmin === 'boolean'
  );
}

export const TOKEN_PARAM = 'token';
export const LOGIN_ERROR_PARAM = 'error';
export const CONFIRM_PARAM = 'confirm';

export function moderationTemplatePath(templateId: string): string {
  return generatePath(ROUTES.MODERATION_TEMPLATE, { templateId });
}

export function officialTemplateEditorPath(templateId: string): string {
  return generatePath(ROUTES.MODERATION_OFFICIAL_TEMPLATE, { templateId });
}

export function moderationAccountPath(accountId: string): string {
  return generatePath(ROUTES.MODERATION_ACCOUNT, { accountId });
}
