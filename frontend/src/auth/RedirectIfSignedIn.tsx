import { Navigate, Outlet, useLocation } from 'react-router';

import { useCurrentUser } from '../api/auth';
import { pathAfterSignIn } from './signInRedirect';

export function RedirectIfSignedIn() {
  const { data: user } = useCurrentUser();
  const location = useLocation();

  if (user) return <Navigate to={pathAfterSignIn(location)} replace />;
  return <Outlet />;
}
