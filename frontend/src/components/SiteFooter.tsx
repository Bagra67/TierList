import { LegalLinks } from './LegalLinks';

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
