import { cn } from 'cn';

import { PAGE_WIDTH_CLASS } from '../constants/layout';
import { LegalLinks } from './LegalLinks';

// Pied de page de toutes les pages, connecté ou non (connexion, salle en invité, résultats
// publics) : les pages légales y sont toujours accessibles
export function SiteFooter() {
  return (
    <footer className="shrink-0 border-t text-xs text-muted-foreground">
      {/* Aligné sur la largeur des pages, comme l'en-tête */}
      <LegalLinks
        className={cn(
          'mx-auto flex w-full flex-wrap gap-x-4 gap-y-1 px-4 py-3',
          PAGE_WIDTH_CLASS.app,
        )}
        linkClassName="underline-offset-4 hover:underline"
      />
    </footer>
  );
}
