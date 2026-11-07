import { useTranslation } from 'react-i18next';
import { Link, useSearchParams } from 'react-router';

import { useVerifyEmail } from '../api/auth';
import { CenteredCardPage } from '../components/CenteredCardPage';
import { ErrorMessage } from '../components/ErrorMessage';
import { Button } from '../components/ui/button';
import { ROUTES, TOKEN_PARAM } from '../constants/routes';
import { translateError } from '../errors/apiError';

export function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get(TOKEN_PARAM);
  const verifyMutation = useVerifyEmail();
  const { t } = useTranslation();

  return (
    <CenteredCardPage title={t('auth.verifyEmail.title')}>
      {token === null ? (
        <ErrorMessage>{t('auth.verifyEmail.missingToken')}</ErrorMessage>
      ) : verifyMutation.isSuccess ? (
        <>
          <p role="status">{t('auth.verifyEmail.success')}</p>
          <Button asChild className="w-full">
            <Link to={ROUTES.HOME}>{t('auth.verifyEmail.continue')}</Link>
          </Button>
        </>
      ) : (
        <>
          <p>{t('auth.verifyEmail.intro')}</p>
          {verifyMutation.isError && (
            <ErrorMessage>{translateError(t, verifyMutation.error)}</ErrorMessage>
          )}
          <Button
            type="button"
            className="w-full"
            disabled={verifyMutation.isPending}
            onClick={() => verifyMutation.mutate(token)}
          >
            {verifyMutation.isPending
              ? t('auth.verifyEmail.submitting')
              : t('auth.verifyEmail.submit')}
          </Button>
        </>
      )}
    </CenteredCardPage>
  );
}
