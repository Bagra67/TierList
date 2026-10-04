import { useTranslation } from 'react-i18next';
import { Navigate, Outlet, useLocation } from 'react-router';

import { useCurrentUser } from '../api/auth';
import { ROUTES } from '../constants/routes';
import { ErrorMessage } from '../components/ErrorMessage';
import { signInRedirectState } from './signInRedirect';

// Garde des pages privées : redirige vers /login sans session. Confort d'interface seulement,
// la vraie protection est la vérification de l'access token par le backend.
export function RequireAuth() {
  const { data: user, isPending, isError } = useCurrentUser();
  const location = useLocation();
  const { t } = useTranslation();

  if (isPending) return <p className="p-4 text-muted-foreground">{t('common.loading')}</p>;
  if (isError) return <ErrorMessage className="p-4">{t('common.backendUnreachable')}</ErrorMessage>;
  if (user === null)
    return <Navigate to={ROUTES.LOGIN} replace state={signInRedirectState(location)} />;
  return <Outlet />;
}
