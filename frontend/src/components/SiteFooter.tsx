import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import { ROUTES } from '../constants/routes';

// Pied de page de toutes les pages, connecté ou non (connexion, salle en invité, résultats
// publics) : les pages légales y sont toujours accessibles
export function SiteFooter() {
  const { t } = useTranslation();

  return (
    <footer className="shrink-0 border-t px-4 py-3 text-xs text-muted-foreground">
      <Link to={ROUTES.PRIVACY} className="underline-offset-4 hover:underline">
        {t('footer.privacy')}
      </Link>
    </footer>
  );
}
