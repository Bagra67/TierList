import { Outlet } from 'react-router';

import { useCurrentUser } from '../api/auth';
import { NotFoundPage } from '../pages/NotFoundPage';
import { isSuperAdmin } from './superAdmin';

export function RequireSuperAdmin() {
  const { data: user } = useCurrentUser();

  if (!isSuperAdmin(user)) return <NotFoundPage />;
  return <Outlet />;
}
