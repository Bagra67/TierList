// Pages du frontend (react-router). /login et / sont aussi les cibles des redirections du
// backend au retour de Google (backend/app/constants/auth.py : FRONTEND_LOGIN, FRONTEND_HOME).
export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  // Lien envoyé par email (backend/app/constants/auth.py : FRONTEND_VERIFY_EMAIL)
  VERIFY_EMAIL: '/verify-email',
} as const;

// Token du lien reçu par email (backend : TOKEN_PARAM)
export const TOKEN_PARAM = 'token';

// Paramètres de requête posés par le backend au retour de Google
export const LOGIN_ERROR_PARAM = 'error';
export const CONFIRM_PARAM = 'confirm';
