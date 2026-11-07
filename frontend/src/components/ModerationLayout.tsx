import { useTranslation } from 'react-i18next';
import { NavLink, Outlet } from 'react-router';
import { cn } from 'cn';

import { PageContainer } from './PageContainer';
import { ROUTES } from '../constants/routes';

export function ModerationLayout() {
  const { t } = useTranslation();

  function linkClassName({ isActive }: { isActive: boolean }) {
    return cn(
      'block rounded-lg px-3 py-2 text-sm whitespace-nowrap hover:bg-muted',
      isActive ? 'bg-muted font-semibold' : 'text-muted-foreground',
    );
  }

  return (
    <PageContainer width="app" className="flex flex-col gap-6 md:flex-row">
      <nav aria-label={t('moderation.nav.label')} className="shrink-0 md:w-48">
        <ul className="flex flex-wrap gap-1 md:flex-col">
          <li>
            <NavLink to={ROUTES.MODERATION_REPORTS} className={linkClassName}>
              {t('moderation.nav.reports')}
            </NavLink>
          </li>
          <li>
            <NavLink to={ROUTES.MODERATION_UPLOADS} className={linkClassName}>
              {t('moderation.nav.uploads')}
            </NavLink>
          </li>
          <li>
            <NavLink to={ROUTES.MODERATION_ACCOUNTS} className={linkClassName}>
              {t('moderation.nav.accounts')}
            </NavLink>
          </li>
          <li>
            <NavLink to={ROUTES.MODERATION_LOG} className={linkClassName}>
              {t('moderation.nav.log')}
            </NavLink>
          </li>
        </ul>
      </nav>
      <div className="min-w-0 flex-1">
        <Outlet />
      </div>
    </PageContainer>
  );
}
