export const PASSWORD_MAX_LENGTH = 128;
export const DISPLAY_NAME_MAX_LENGTH = 50;

export const GOOGLE_SIGN_IN_PATH = '/api/auth/google/login';
export const GOOGLE_ACCOUNT_BANNED = 'google_account_banned';
export const DELETE_ACCOUNT_STEP = 'delete-account';
export type GoogleNextStep = typeof DELETE_ACCOUNT_STEP;

export const SESSION_PATHS: ReadonlySet<string> = new Set([
  '/auth/register',
  '/auth/login',
  '/auth/refresh',
  '/auth/logout',
]);

export const CURRENT_USER_QUERY_KEY = ['auth', 'me'] as const;
export const GOOGLE_BAN_NOTICE_QUERY_KEY = ['auth', 'google-ban-notice'] as const;
