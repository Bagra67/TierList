import { useTranslation } from 'react-i18next';
import { NavLink } from 'react-router';

import { useCurrentUser } from '../api/auth';
import { ROUTES } from '../constants/routes';
import { cn } from '@/lib/utils';

// Liens vers les pages privées, affichés seulement une fois connecté. NavLink pose
// aria-current="page" sur le lien de la page affichée.
export function MainNav() {
  const { data: user } = useCurrentUser();
  const { t } = useTranslation();

  if (!user) return null;

  function linkClassName({ isActive }: { isActive: boolean }) {
    return cn(
      'text-sm underline-offset-4 hover:underline',
      isActive ? 'font-semibold' : 'text-muted-foreground',
    );
  }

  return (
    <nav aria-label={t('nav.label')}>
      <ul className="flex flex-wrap items-center gap-4">
        <li>
          <NavLink to={ROUTES.HOME} end className={linkClassName}>
            {t('nav.home')}
          </NavLink>
        </li>
        <li>
          <NavLink to={ROUTES.TEMPLATES} className={linkClassName}>
            {t('nav.templates')}
          </NavLink>
        </li>
      </ul>
    </nav>
  );
}
