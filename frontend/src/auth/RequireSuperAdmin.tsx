import { Outlet } from 'react-router';

import { useCurrentUser } from '../api/auth';
import { NotFoundPage } from '../pages/NotFoundPage';
import { isSuperAdmin } from './superAdmin';

// Garde de l'espace de modération, placée dans RequireAuth (le compte est donc déjà chargé). Les
// autres comptes voient la page introuvable : l'espace reste invisible. Confort d'interface
// seulement, le backend refuse la modération à qui n'est pas super admin (403).
export function RequireSuperAdmin() {
  const { data: user } = useCurrentUser();

  if (!isSuperAdmin(user)) return <NotFoundPage />;
  return <Outlet />;
}
