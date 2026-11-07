import { Trans } from 'react-i18next';
import { Link } from 'react-router';

import { ROUTES } from '../constants/routes';
import { textLinkClassName } from './ui/text-link';

interface TermsAcceptanceProps {
  i18nKey: 'auth.acceptTerms.register' | 'auth.acceptTerms.google';
}

export function TermsAcceptance({ i18nKey }: TermsAcceptanceProps) {
  return (
    <p className="text-center text-xs text-muted-foreground">
      <Trans
        i18nKey={i18nKey}
        components={{
          terms: <Link to={ROUTES.TERMS} className={textLinkClassName} />,
          privacy: <Link to={ROUTES.PRIVACY} className={textLinkClassName} />,
        }}
      />
    </p>
  );
}
