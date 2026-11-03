import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import { AuthPageShell } from '../components/AuthPageShell';
import { Button } from '../components/ui/button';
import { ROUTES } from '../constants/routes';

export function NotFoundPage() {
  const { t } = useTranslation();

  return (
    <AuthPageShell title={t('notFound.title')}>
      <p>{t('notFound.message')}</p>
      <Button asChild className="w-full">
        <Link to={ROUTES.HOME}>{t('notFound.backHome')}</Link>
      </Button>
    </AuthPageShell>
  );
}
