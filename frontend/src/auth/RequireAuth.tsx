import { useTranslation } from 'react-i18next';
import { Navigate, Outlet, useLocation } from 'react-router';

import { useCurrentUser } from '../api/auth';
import { ROUTES } from '../constants/routes';

// Garde des pages privées : redirige vers /login sans session. Confort d'interface seulement,
// la vraie protection est la vérification de l'access token par le backend.
export function RequireAuth() {
  const { data: user, isPending, isError } = useCurrentUser();
  const location = useLocation();
  const { t } = useTranslation();

  if (isPending) return <p>{t('common.loading')}</p>;
  if (isError) return <p role="alert">{t('common.backendUnreachable')}</p>;
  if (user === null)
    return <Navigate to={ROUTES.LOGIN} replace state={{ from: location.pathname }} />;
  return <Outlet />;
}
