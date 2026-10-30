import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import { ROUTES } from '../constants/routes';

// Les trois pages légales, toujours accessibles : pied de page et panneau de paramètres
interface LegalLinksProps {
  className: string;
  linkClassName: string;
}

export function LegalLinks({ className, linkClassName }: LegalLinksProps) {
  const { t } = useTranslation();

  return (
    <div className={className}>
      <Link to={ROUTES.PRIVACY} className={linkClassName}>
        {t('footer.privacy')}
      </Link>
      <Link to={ROUTES.TERMS} className={linkClassName}>
        {t('footer.terms')}
      </Link>
      <Link to={ROUTES.LEGAL_NOTICE} className={linkClassName}>
        {t('footer.legalNotice')}
      </Link>
    </div>
  );
}
