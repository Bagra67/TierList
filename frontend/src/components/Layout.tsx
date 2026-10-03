import { Outlet } from 'react-router';

import { LanguageSwitcher } from './LanguageSwitcher';

// Cadre commun à toutes les pages : le sélecteur de langue reste accessible partout
export function Layout() {
  return (
    <>
      <header className="flex justify-end border-b px-4 py-2">
        <LanguageSwitcher />
      </header>
      <Outlet />
    </>
  );
}
