import { generatePath } from 'react-router';

// Pages du frontend (react-router). /login et / sont aussi les cibles des redirections du
// backend au retour de Google (backend/app/constants/auth.py : FRONTEND_LOGIN, FRONTEND_HOME).
export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  // Lien envoyé par email (backend/app/constants/auth.py : FRONTEND_VERIFY_EMAIL)
  VERIFY_EMAIL: '/verify-email',
  FORGOT_PASSWORD: '/forgot-password',
  // Lien envoyé par email (backend/app/constants/auth.py : FRONTEND_RESET_PASSWORD)
  RESET_PASSWORD: '/reset-password',
  TEMPLATES: '/templates',
  TEMPLATE_EDITOR: '/templates/:templateId',
  HISTORY: '/history',
  MODERATION: '/moderation',
  MODERATION_UPLOADS: '/moderation/uploads',
  MODERATION_ACCOUNTS: '/moderation/accounts',
  MODERATION_ACCOUNT: '/moderation/accounts/:accountId',
  MODERATION_LOG: '/moderation/log',
  // Lobby d'une salle, cible du lien partagé (backend/app/constants/rooms.py : FRONTEND_ROOM)
  ROOM: '/r/:code',
  RESULTS: '/results/:token',
  PRIVACY: '/privacy',
  TERMS: '/terms',
  LEGAL_NOTICE: '/legal',
} as const;

export function templateEditorPath(templateId: string): string {
  return generatePath(ROUTES.TEMPLATE_EDITOR, { templateId });
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

// Token du lien reçu par email (backend : TOKEN_PARAM)
export const TOKEN_PARAM = 'token';

// Paramètres de requête posés par le backend au retour de Google
export const LOGIN_ERROR_PARAM = 'error';
export const CONFIRM_PARAM = 'confirm';

export function moderationAccountPath(accountId: string): string {
  return generatePath(ROUTES.MODERATION_ACCOUNT, { accountId });
}
