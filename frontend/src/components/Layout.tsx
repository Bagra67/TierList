import { Outlet } from 'react-router';

import { LanguageSwitcher } from './LanguageSwitcher';
import { MainNav } from './MainNav';
import { ThemeSwitcher } from './ThemeSwitcher';

// Cadre commun à toutes les pages : les sélecteurs de thème et de langue restent accessibles
// partout, la navigation apparaît une fois connecté
export function Layout() {
  return (
    <>
      <header className="flex flex-wrap items-center justify-between gap-4 border-b px-4 py-2">
        <MainNav />
        <div className="ml-auto flex flex-wrap gap-4">
          <ThemeSwitcher />
          <LanguageSwitcher />
        </div>
      </header>
      <Outlet />
    </>
  );
}
