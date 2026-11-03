import { Outlet } from 'react-router';

import { useForgetEndedSession } from '../api/auth';
import { Logo } from './Logo';
import { LogoutButton } from './LogoutButton';
import { MainNav } from './MainNav';
import { SettingsPanel } from './SettingsPanel';
import { SiteFooter } from './SiteFooter';

export function Layout() {
  useForgetEndedSession();
  return (
    <div className="flex min-h-dvh flex-col lg:h-dvh">
      <header className="flex shrink-0 flex-wrap items-center justify-between gap-4 border-b px-4 py-2">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
          <Logo />
          <MainNav />
        </div>
        <div className="ml-auto flex flex-wrap items-center gap-4">
          <LogoutButton />
          <SettingsPanel />
        </div>
      </header>
      <div className="flex flex-1 flex-col lg:min-h-0 lg:overflow-y-auto">
        <Outlet />
      </div>
      <SiteFooter />
    </div>
  );
}
