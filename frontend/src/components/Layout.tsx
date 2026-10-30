import { cn } from 'cn';
import { Outlet } from 'react-router';

import { useForgetEndedSession } from '../api/auth';
import { PAGE_WIDTH_CLASS } from '../constants/layout';
import { Logo } from './Logo';
import { LogoutButton } from './LogoutButton';
import { MainNav } from './MainNav';
import { SettingsPanel } from './SettingsPanel';
import { SiteFooter } from './SiteFooter';

// Cadre commun à toutes les pages : le panneau de paramètres (thème, langue, compte) et le pied de
// page (pages légales) restent accessibles partout, la navigation et « Se déconnecter »
// apparaissent une fois connecté. Le pied de page est en bas de la fenêtre même quand la page est
// courte. Sur grand écran, le cadre fait la hauteur de la fenêtre et seul le contenu défile, entre
// l'en-tête et le pied de page, toujours visibles : une page comme l'éditeur peut ainsi remplir
// l'écran exactement et faire défiler ses colonnes plutôt que toute la page.
export function Layout() {
  useForgetEndedSession();
  return (
    <div className="flex min-h-dvh flex-col lg:h-dvh">
      {/* La bordure fait toute la fenêtre ; le contenu s'aligne sur la largeur des pages */}
      <header className="shrink-0 border-b">
        <div
          className={cn(
            'mx-auto flex w-full flex-wrap items-center justify-between gap-4 px-4 py-2',
            PAGE_WIDTH_CLASS.app,
          )}
        >
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
            <Logo />
            <MainNav />
          </div>
          <div className="ml-auto flex flex-wrap items-center gap-4">
            <LogoutButton />
            <SettingsPanel />
          </div>
        </div>
      </header>
      <div className="flex flex-1 flex-col lg:min-h-0 lg:overflow-y-auto">
        <Outlet />
      </div>
      <SiteFooter />
    </div>
  );
}
