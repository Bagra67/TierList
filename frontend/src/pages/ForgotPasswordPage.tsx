import type { FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import { useForgotPassword } from '../api/auth';
import { AuthPageShell } from '../components/AuthPageShell';
import { ErrorMessage } from '../components/ErrorMessage';
import { TextField } from '../components/TextField';
import { Button } from '../components/ui/button';
import { ROUTES } from '../constants/routes';
import { getFieldErrors, translateError, translateFieldError } from '../errors/apiError';

export function ForgotPasswordPage() {
  const forgotMutation = useForgotPassword();
  const fieldErrors = getFieldErrors(forgotMutation.error);
  const { t } = useTranslation();

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    forgotMutation.mutate(String(new FormData(event.currentTarget).get('email')));
  }

  return (
    <AuthPageShell
      title={t('auth.forgotPassword.title')}
      footer={
        <Link to={ROUTES.LOGIN} className="font-medium underline underline-offset-4">
          {t('auth.forgotPassword.backToLogin')}
        </Link>
      }
    >
      {forgotMutation.isSuccess ? (
        // Même message que le compte existe ou non : la page ne révèle pas qui est inscrit
        <p role="status">{t('auth.forgotPassword.sent')}</p>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <p>{t('auth.forgotPassword.intro')}</p>
          <TextField
            label={t('auth.email')}
            name="email"
            type="email"
            autoComplete="email"
            required
            error={translateFieldError(t, fieldErrors.email)}
          />
          {forgotMutation.isError && (
            <ErrorMessage>{translateError(t, forgotMutation.error)}</ErrorMessage>
          )}
          <Button type="submit" disabled={forgotMutation.isPending} className="w-full">
            {forgotMutation.isPending
              ? t('auth.forgotPassword.submitting')
              : t('auth.forgotPassword.submit')}
          </Button>
        </form>
      )}
    </AuthPageShell>
  );
}
