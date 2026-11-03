import type { User } from '../api/auth';

export function isSuperAdmin(user: User | null | undefined): boolean {
  return user?.role === 'super_admin';
}
