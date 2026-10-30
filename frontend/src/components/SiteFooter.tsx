import { LegalLinks } from './LegalLinks';

// Pied de page de toutes les pages, connecté ou non (connexion, salle en invité, résultats
// publics) : les pages légales y sont toujours accessibles
export function SiteFooter() {
  return (
    <footer className="shrink-0 border-t px-4 py-3 text-xs text-muted-foreground">
      <LegalLinks
        className="flex flex-wrap gap-x-4 gap-y-1"
        linkClassName="underline-offset-4 hover:underline"
      />
    </footer>
  );
}
