import { useTranslation } from 'react-i18next';
import { NavLink } from 'react-router';

import { useCurrentUser } from '../api/auth';
import { useOpenReportCount } from '../api/moderation';
import { isSuperAdmin } from '../auth/superAdmin';
import { ROUTES } from '../constants/routes';
import { cn } from 'cn';

export function MainNav() {
  const { data: user } = useCurrentUser();
  const { t } = useTranslation();
  const { data: openReports } = useOpenReportCount(user !== undefined && isSuperAdmin(user));

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
        <li>
          <NavLink to={ROUTES.HISTORY} className={linkClassName}>
            {t('nav.history')}
          </NavLink>
        </li>
        {isSuperAdmin(user) && (
          <li>
            <NavLink to={ROUTES.MODERATION} className={linkClassName}>
              {t('nav.moderation')}
              {openReports !== undefined && openReports > 0 && (
                <span
                  aria-label={t('nav.openReports', { count: openReports })}
                  className="ml-1.5 rounded-full bg-muted px-1.5 py-0.5 text-xs font-semibold text-foreground"
                >
                  {openReports}
                </span>
              )}
            </NavLink>
          </li>
        )}
      </ul>
    </nav>
  );
}
