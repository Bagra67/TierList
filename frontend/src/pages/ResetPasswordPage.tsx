import type { FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useSearchParams } from 'react-router';

import { useResetPassword } from '../api/auth';
import { AuthPageShell } from '../components/AuthPageShell';
import { ErrorMessage } from '../components/ErrorMessage';
import { TextField } from '../components/TextField';
import { Button } from '../components/ui/button';
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
    <AuthPageShell title={t('auth.resetPassword.title')}>
      {token === null ? (
        <ErrorMessage>{t('auth.resetPassword.missingToken')}</ErrorMessage>
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
            <ErrorMessage>{translateError(t, resetMutation.error)}</ErrorMessage>
          )}
          <Button type="submit" disabled={resetMutation.isPending} className="w-full">
            {resetMutation.isPending
              ? t('auth.resetPassword.submitting')
              : t('auth.resetPassword.submit')}
          </Button>
        </form>
      )}
    </AuthPageShell>
  );
}
