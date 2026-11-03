import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import { CenteredCardPage } from '../components/CenteredCardPage';
import { Button } from '../components/ui/button';
import { ROUTES } from '../constants/routes';

export function NotFoundPage() {
  const { t } = useTranslation();

  return (
    <CenteredCardPage title={t('notFound.title')}>
      <p>{t('notFound.message')}</p>
      <Button asChild className="w-full">
        <Link to={ROUTES.HOME}>{t('notFound.backHome')}</Link>
      </Button>
    </CenteredCardPage>
  );
}
