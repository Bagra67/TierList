import { useTranslation } from 'react-i18next';

import { googleSignInUrl } from '../api/auth';

export function GoogleSignInLink() {
  const { t } = useTranslation();
  return <a href={googleSignInUrl()}>{t('auth.continueWithGoogle')}</a>;
}
