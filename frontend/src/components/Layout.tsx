import { Outlet } from 'react-router';

import { LanguageSwitcher } from './LanguageSwitcher';
import { ThemeSwitcher } from './ThemeSwitcher';

// Cadre commun à toutes les pages : les sélecteurs de thème et de langue restent accessibles partout
export function Layout() {
  return (
    <>
      <header className="flex flex-wrap justify-end gap-4 border-b px-4 py-2">
        <ThemeSwitcher />
        <LanguageSwitcher />
      </header>
      <Outlet />
    </>
  );
}
