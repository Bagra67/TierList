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
  // Lobby d'une salle, cible du lien partagé (backend/app/constants/rooms.py : FRONTEND_ROOM)
  ROOM: '/r/:code',
  // Résultats d'une partie close, ouverts sans compte par leur lien (US-5.3)
  RESULTS: '/results/:token',
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

// État de navigation posé par le lobby en ouvrant des résultats : la salle d'où l'on vient, et si
// le lecteur en est le room admin (il peut alors rejouer, US-2.9). Un visiteur arrivé par le lien
// public n'en a pas
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
