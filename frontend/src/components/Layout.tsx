import { Outlet } from 'react-router';

import { LanguageSwitcher } from './LanguageSwitcher';
import { MainNav } from './MainNav';
import { ThemeSwitcher } from './ThemeSwitcher';

// Cadre commun à toutes les pages : les sélecteurs de thème et de langue restent accessibles
// partout, la navigation apparaît une fois connecté. Sur grand écran, le cadre fait la hauteur de
// la fenêtre et seul le contenu défile, sous l'en-tête : une page comme l'éditeur peut ainsi
// remplir l'écran exactement et faire défiler ses colonnes plutôt que toute la page.
export function Layout() {
  return (
    <div className="lg:flex lg:h-dvh lg:flex-col">
      <header className="flex shrink-0 flex-wrap items-center justify-between gap-4 border-b px-4 py-2">
        <MainNav />
        <div className="ml-auto flex flex-wrap gap-4">
          <ThemeSwitcher />
          <LanguageSwitcher />
        </div>
      </header>
      <div className="lg:flex lg:min-h-0 lg:flex-1 lg:flex-col lg:overflow-y-auto">
        <Outlet />
      </div>
    </div>
  );
}
