import 'i18next';

import type { fr } from './locales/fr';

// Clés de traduction typées : t('auth.login.title') est vérifié par pnpm typecheck
declare module 'i18next' {
  interface CustomTypeOptions {
    defaultNS: 'translation';
    resources: { translation: typeof fr };
  }
}
