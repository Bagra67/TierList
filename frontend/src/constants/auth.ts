// Doivent rester égales aux limites du backend (backend/app/constants/auth.py), liées au schéma
// de la base. La longueur minimale du mot de passe, elle, est un réglage du backend
// (PASSWORD_MIN_LENGTH) : le frontend ne la connaît pas et la lit dans les params de la 422.
export const PASSWORD_MAX_LENGTH = 128;
export const DISPLAY_NAME_MAX_LENGTH = 50;

// Connexion avec Google : navigation complète vers le backend (via le proxy /api)
export const GOOGLE_SIGN_IN_PATH = '/api/auth/google/login';
// Étape reprise après une reconnexion Google (seule valeur acceptée par le backend)
export const DELETE_ACCOUNT_STEP = 'delete-account';
export type GoogleNextStep = typeof DELETE_ACCOUNT_STEP;

// Routes qui ouvrent ou ferment la session : leur 401 (identifiants faux, session expirée)
// est la réponse attendue, il ne faut pas tenter de rafraîchir (ni boucler sur /auth/refresh).
export const SESSION_PATHS: ReadonlySet<string> = new Set([
  '/auth/register',
  '/auth/login',
  '/auth/refresh',
  '/auth/logout',
]);

// Entrée du cache TanStack Query qui contient l'utilisateur connecté (ou null)
export const CURRENT_USER_QUERY_KEY = ['auth', 'me'] as const;
