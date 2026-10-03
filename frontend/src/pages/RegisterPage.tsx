import type { FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router';

import { useRegister } from '../api/auth';
import { DISPLAY_NAME_MAX_LENGTH, PASSWORD_MAX_LENGTH } from '../constants/auth';
import { ROUTES } from '../constants/routes';
import { getFieldErrors, translateError, translateFieldError } from '../errors/apiError';
import { GoogleSignInLink } from '../components/GoogleSignInLink';
import { TextField } from '../components/TextField';

export function RegisterPage() {
  const registerMutation = useRegister();
  const navigate = useNavigate();
  const fieldErrors = getFieldErrors(registerMutation.error);
  const { t } = useTranslation();

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await registerMutation.mutateAsync({
        email: String(form.get('email')),
        password: String(form.get('password')),
        display_name: String(form.get('display_name')),
      });
    } catch {
      return; // l'erreur est affichée depuis registerMutation.error
    }
    await navigate(ROUTES.HOME, { replace: true });
  }

  return (
    <main>
      <h1>{t('auth.register.title')}</h1>
      <form onSubmit={handleSubmit}>
        <TextField
          label={t('auth.displayName')}
          name="display_name"
          autoComplete="nickname"
          required
          maxLength={DISPLAY_NAME_MAX_LENGTH}
          error={translateFieldError(t, fieldErrors.display_name)}
        />
        <TextField
          label={t('auth.email')}
          name="email"
          type="email"
          autoComplete="email"
          required
          error={translateFieldError(t, fieldErrors.email)}
        />
        <TextField
          label={t('auth.password')}
          name="password"
          type="password"
          autoComplete="new-password"
          required
          maxLength={PASSWORD_MAX_LENGTH}
          error={translateFieldError(t, fieldErrors.password)}
        />
        {registerMutation.isError && (
          <p role="alert">{translateError(t, registerMutation.error)}</p>
        )}
        <button type="submit" disabled={registerMutation.isPending}>
          {registerMutation.isPending ? t('auth.register.submitting') : t('auth.register.submit')}
        </button>
      </form>
      <p>
        <GoogleSignInLink />
      </p>
      <p>
        {t('auth.register.hasAccount')}{' '}
        <Link to={ROUTES.LOGIN}>{t('auth.register.loginLink')}</Link>
      </p>
    </main>
  );
}
