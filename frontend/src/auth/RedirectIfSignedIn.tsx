import { Navigate, Outlet, useLocation } from 'react-router';

import { useCurrentUser } from '../api/auth';
import { pathAfterSignIn } from './signInRedirect';

// Garde des pages de connexion et d'inscription : un utilisateur déjà connecté est renvoyé là
// où il allait. Pendant le chargement de la session, la page s'affiche normalement.
export function RedirectIfSignedIn() {
  const { data: user } = useCurrentUser();
  const location = useLocation();

  if (user) return <Navigate to={pathAfterSignIn(location)} replace />;
  return <Outlet />;
}
