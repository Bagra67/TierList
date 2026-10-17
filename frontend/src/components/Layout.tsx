import { Outlet } from 'react-router';

import { useForgetEndedSession } from '../api/auth';
import { LanguageSwitcher } from './LanguageSwitcher';
import { LogoutButton } from './LogoutButton';
import { MainNav } from './MainNav';
import { ThemeSwitcher } from './ThemeSwitcher';

// Cadre commun à toutes les pages : les sélecteurs de thème et de langue restent accessibles
// partout, la navigation et « Se déconnecter » apparaissent une fois connecté. Sur grand écran, le cadre fait la hauteur de
// la fenêtre et seul le contenu défile, sous l'en-tête : une page comme l'éditeur peut ainsi
// remplir l'écran exactement et faire défiler ses colonnes plutôt que toute la page.
export function Layout() {
  useForgetEndedSession();
  return (
    <div className="lg:flex lg:h-dvh lg:flex-col">
      <header className="flex shrink-0 flex-wrap items-center justify-between gap-4 border-b px-4 py-2">
        <MainNav />
        <div className="ml-auto flex flex-wrap items-center gap-4">
          <ThemeSwitcher />
          <LanguageSwitcher />
          <LogoutButton />
        </div>
      </header>
      <div className="lg:flex lg:min-h-0 lg:flex-1 lg:flex-col lg:overflow-y-auto">
        <Outlet />
      </div>
    </div>
  );
}
