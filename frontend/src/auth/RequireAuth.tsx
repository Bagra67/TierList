import { useTranslation } from 'react-i18next';
import { Navigate, Outlet, useLocation } from 'react-router';

import { useCurrentUser } from '../api/auth';
import { ROUTES } from '../constants/routes';
import { ErrorMessage } from '../components/ErrorMessage';
import { signInRedirectState } from './signInRedirect';
import { LoadingSkeleton } from '../components/LoadingSkeleton';

// Garde des pages privées : redirige vers /login sans session. Confort d'interface seulement,
// la vraie protection est la vérification de l'access token par le backend.
export function RequireAuth() {
  const { data: user, isPending, isError } = useCurrentUser();
  const location = useLocation();
  const { t } = useTranslation();

  if (isPending)
    return (
      <div className="mx-auto w-full max-w-2xl px-4 py-10">
        <LoadingSkeleton shape="list" />
      </div>
    );
  if (isError) return <ErrorMessage className="m-4">{t('common.backendUnreachable')}</ErrorMessage>;
  if (user === null)
    return <Navigate to={ROUTES.LOGIN} replace state={signInRedirectState(location)} />;
  return <Outlet />;
}
