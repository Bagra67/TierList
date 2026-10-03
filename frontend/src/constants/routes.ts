// Pages du frontend (react-router). /login et / sont aussi les cibles des redirections du
// backend au retour de Google (backend/app/constants/auth.py : FRONTEND_LOGIN, FRONTEND_HOME).
export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  REGISTER: '/register',
} as const;

// Paramètres de requête posés par le backend au retour de Google
export const LOGIN_ERROR_PARAM = 'error';
export const CONFIRM_PARAM = 'confirm';
