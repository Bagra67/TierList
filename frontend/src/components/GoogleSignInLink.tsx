import { useTranslation } from 'react-i18next';
import { type Location, useLocation } from 'react-router';

import { googleSignInUrl } from '../api/auth';
import { publicTemplateIdAfterSignIn } from '../auth/signInRedirect';
import { Button } from './ui/button';

export function GoogleSignInLink() {
  const { t } = useTranslation();
  const location: Location = useLocation();
  return (
    <Button asChild variant="outline" className="w-full">
      <a href={googleSignInUrl({ templateId: publicTemplateIdAfterSignIn(location) })}>
        {t('auth.continueWithGoogle')}
      </a>
    </Button>
  );
}
