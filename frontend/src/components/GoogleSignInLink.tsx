import { useTranslation } from 'react-i18next';
import { type Location, useLocation } from 'react-router';

import { googleSignInUrl } from '../api/auth';
import { pathAfterSignIn } from '../auth/signInRedirect';
import { ROUTES } from '../constants/routes';
import { Button } from './ui/button';

export function GoogleSignInLink() {
  const { t } = useTranslation();
  const location: Location = useLocation();
  const requestedPath: string = pathAfterSignIn(location);
  const returnTo: string | undefined = requestedPath === ROUTES.HOME ? undefined : requestedPath;
  return (
    <Button asChild variant="outline" className="w-full">
      <a href={googleSignInUrl({ returnTo })}>{t('auth.continueWithGoogle')}</a>
    </Button>
  );
}
