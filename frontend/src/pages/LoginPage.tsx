import type { FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router';

import { useLogin } from '../api/auth';
import { PASSWORD_MAX_LENGTH } from '../constants/auth';
import { LOGIN_ERROR_PARAM, ROUTES } from '../constants/routes';
import { getFieldErrors, translateError, translateFieldError } from '../errors/apiError';
import { translateGoogleError } from '../errors/googleError';
import { GoogleSignInLink } from '../components/GoogleSignInLink';
import { TextField } from '../components/TextField';

export function LoginPage() {
  const loginMutation = useLogin();
  const navigate = useNavigate();
  const location = useLocation();
  const fieldErrors = getFieldErrors(loginMutation.error);
  const [searchParams] = useSearchParams();
  const googleError = searchParams.get(LOGIN_ERROR_PARAM);
  const { t } = useTranslation();

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await loginMutation.mutateAsync({
        email: String(form.get('email')),
        password: String(form.get('password')),
      });
    } catch {
      return; // l'erreur est affichée depuis loginMutation.error
    }
    const from = (location.state as { from?: string } | null)?.from ?? ROUTES.HOME;
    await navigate(from, { replace: true });
  }

  return (
    <main>
      <h1>{t('auth.login.title')}</h1>
      {googleError !== null && <p role="alert">{translateGoogleError(t, googleError)}</p>}
      <form onSubmit={handleSubmit}>
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
          autoComplete="current-password"
          required
          maxLength={PASSWORD_MAX_LENGTH}
          error={translateFieldError(t, fieldErrors.password)}
        />
        {loginMutation.isError && <p role="alert">{translateError(t, loginMutation.error)}</p>}
        <button type="submit" disabled={loginMutation.isPending}>
          {loginMutation.isPending ? t('auth.login.submitting') : t('auth.login.submit')}
        </button>
      </form>
      <p>
        <GoogleSignInLink />
      </p>
      <p>
        {t('auth.login.noAccount')} <Link to={ROUTES.REGISTER}>{t('auth.login.registerLink')}</Link>
      </p>
    </main>
  );
}
