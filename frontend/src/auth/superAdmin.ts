import type { User } from '../api/auth';

// Rôle donné hors de l'application (US-1.1). Sert seulement à montrer ou cacher l'espace de
// modération : le backend vérifie le rôle à chaque route de modération.
export function isSuperAdmin(user: User | null | undefined): boolean {
  return user?.role === 'super_admin';
}
