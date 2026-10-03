import type { FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useSearchParams } from 'react-router';

import { useResetPassword } from '../api/auth';
import { TextField } from '../components/TextField';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader } from '../components/ui/card';
import { PASSWORD_MAX_LENGTH } from '../constants/auth';
import { ROUTES, TOKEN_PARAM } from '../constants/routes';
import { getFieldErrors, translateError, translateFieldError } from '../errors/apiError';

// Page du lien reçu par email : choisit un nouveau mot de passe
export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get(TOKEN_PARAM);
  const resetMutation = useResetPassword();
  const fieldErrors = getFieldErrors(resetMutation.error);
  const { t } = useTranslation();

  function handleSubmit(event: FormEvent<HTMLFormElement>, linkToken: string) {
    event.preventDefault();
    resetMutation.mutate({
      token: linkToken,
      password: String(new FormData(event.currentTarget).get('password')),
    });
  }

  return (
    <main className="mx-auto w-full max-w-sm px-4 py-10">
      <Card>
        <CardHeader>
          <h1 className="text-lg font-semibold">{t('auth.resetPassword.title')}</h1>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {token === null ? (
            <p role="alert" className="text-destructive">
              {t('auth.resetPassword.missingToken')}
            </p>
          ) : resetMutation.isSuccess ? (
            <>
              <p role="status">{t('auth.resetPassword.success')}</p>
              <Button asChild className="w-full">
                <Link to={ROUTES.LOGIN}>{t('auth.resetPassword.signIn')}</Link>
              </Button>
            </>
          ) : (
            <form onSubmit={(event) => handleSubmit(event, token)} className="flex flex-col gap-4">
              <TextField
                label={t('auth.resetPassword.newPassword')}
                name="password"
                type="password"
                autoComplete="new-password"
                required
                maxLength={PASSWORD_MAX_LENGTH}
                error={translateFieldError(t, fieldErrors.password)}
              />
              {resetMutation.isError && (
                <p role="alert" className="text-destructive">
                  {translateError(t, resetMutation.error)}
                </p>
              )}
              <Button type="submit" disabled={resetMutation.isPending} className="w-full">
                {resetMutation.isPending
                  ? t('auth.resetPassword.submitting')
                  : t('auth.resetPassword.submit')}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
