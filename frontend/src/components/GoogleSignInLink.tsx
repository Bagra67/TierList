import { useTranslation } from 'react-i18next';

import { googleSignInUrl } from '../api/auth';
import { Button } from './ui/button';

export function GoogleSignInLink() {
  const { t } = useTranslation();
  return (
    <Button asChild variant="outline" className="w-full">
      <a href={googleSignInUrl()}>{t('auth.continueWithGoogle')}</a>
    </Button>
  );
}
