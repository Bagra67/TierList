import { useTranslation } from 'react-i18next';
import { Link, useSearchParams } from 'react-router';

import { useVerifyEmail } from '../api/auth';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader } from '../components/ui/card';
import { ROUTES, TOKEN_PARAM } from '../constants/routes';
import { translateError } from '../errors/apiError';

// Page du lien reçu par email. La confirmation attend un clic : un outil qui ouvre les liens
// des emails pour les analyser (antispam) ne confirme donc pas l'adresse à la place de
// l'utilisateur.
export function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get(TOKEN_PARAM);
  const verifyMutation = useVerifyEmail();
  const { t } = useTranslation();

  return (
    <main className="mx-auto w-full max-w-sm px-4 py-10">
      <Card>
        <CardHeader>
          <h1 className="text-lg font-semibold">{t('auth.verifyEmail.title')}</h1>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {token === null ? (
            <p role="alert" className="text-destructive">
              {t('auth.verifyEmail.missingToken')}
            </p>
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
                <p role="alert" className="text-destructive">
                  {translateError(t, verifyMutation.error)}
                </p>
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
        </CardContent>
      </Card>
    </main>
  );
}
