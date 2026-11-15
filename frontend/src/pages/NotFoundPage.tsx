import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import { CenteredCardPage } from '../components/CenteredCardPage';
import { Button } from '../components/ui/button';
import { ROUTES } from '../constants/routes';

interface NotFoundPageProps {
  title?: string;
  message?: string;
}

export function NotFoundPage({ title, message }: NotFoundPageProps) {
  const { t } = useTranslation();

  return (
    <CenteredCardPage title={title ?? t('notFound.title')}>
      <p>{message ?? t('notFound.message')}</p>
      <Button asChild className="w-full">
        <Link to={ROUTES.HOME}>{t('notFound.backHome')}</Link>
      </Button>
    </CenteredCardPage>
  );
}
