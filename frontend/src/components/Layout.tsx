import { Outlet } from 'react-router';

import { useForgetEndedSession } from '../api/auth';
import { LogoutButton } from './LogoutButton';
import { MainNav } from './MainNav';
import { SettingsPanel } from './SettingsPanel';
import { SiteFooter } from './SiteFooter';

// Cadre commun à toutes les pages : le panneau de paramètres (thème, langue, compte) et le pied de
// page (pages légales) restent accessibles partout, la navigation et « Se déconnecter »
// apparaissent une fois connecté. Sur grand écran, le cadre fait la hauteur de la fenêtre et seul
// le contenu défile, sous l'en-tête : une page comme l'éditeur peut ainsi remplir l'écran
// exactement et faire défiler ses colonnes plutôt que toute la page.
export function Layout() {
  useForgetEndedSession();
  return (
    <div className="lg:flex lg:h-dvh lg:flex-col">
      <header className="flex shrink-0 flex-wrap items-center justify-between gap-4 border-b px-4 py-2">
        <MainNav />
        <div className="ml-auto flex flex-wrap items-center gap-4">
          <LogoutButton />
          <SettingsPanel />
        </div>
      </header>
      <div className="lg:flex lg:min-h-0 lg:flex-1 lg:flex-col lg:overflow-y-auto">
        <Outlet />
        <SiteFooter />
      </div>
    </div>
  );
}
