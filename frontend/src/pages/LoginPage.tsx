import type { FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router';
import { cn } from 'cn';

import { useLogin } from '../api/auth';
import { pathAfterSignIn } from '../auth/signInRedirect';
import { PASSWORD_MAX_LENGTH } from '../constants/auth';
import { LOGIN_ERROR_PARAM, ROUTES } from '../constants/routes';
import { getFieldErrors, translateError, translateFieldError } from '../errors/apiError';
import { translateGoogleError } from '../errors/googleError';
import { AuthPageShell } from '../components/AuthPageShell';
import { ErrorMessage } from '../components/ErrorMessage';
import { GoogleSignInLink } from '../components/GoogleSignInLink';
import { TermsAcceptance } from '../components/TermsAcceptance';
import { TextField } from '../components/TextField';
import { Button } from '../components/ui/button';
import { textLinkClassName } from '../components/ui/text-link';

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
    await navigate(pathAfterSignIn(location), { replace: true });
  }

  return (
    <AuthPageShell
      title={t('auth.login.title')}
      footer={
        <p>
          {t('auth.login.noAccount')}{' '}
          {/* L'état garde la page demandée, pour y revenir après l'inscription */}
          <Link to={ROUTES.REGISTER} state={location.state} className={textLinkClassName}>
            {t('auth.login.registerLink')}
          </Link>
        </p>
      }
    >
      {googleError !== null && <ErrorMessage>{translateGoogleError(t, googleError)}</ErrorMessage>}
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
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
        {loginMutation.isError && (
          <ErrorMessage>{translateError(t, loginMutation.error)}</ErrorMessage>
        )}
        <Button type="submit" disabled={loginMutation.isPending} className="w-full">
          {loginMutation.isPending ? t('auth.login.submitting') : t('auth.login.submit')}
        </Button>
      </form>
      <Link to={ROUTES.FORGOT_PASSWORD} className={cn(textLinkClassName, 'self-center text-sm')}>
        {t('auth.login.forgotPassword')}
      </Link>
      <GoogleSignInLink />
      {/* Continuer avec Google crée le compte s'il n'existe pas encore */}
      <TermsAcceptance i18nKey="auth.acceptTerms.google" />
    </AuthPageShell>
  );
}
