import type { FormEvent } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router';

import { useLogin } from '../api/auth';
import { PASSWORD_MAX_LENGTH } from '../constants/auth';
import { GOOGLE_ERROR_MESSAGES, GOOGLE_GENERIC_ERROR_MESSAGE } from '../constants/messages';
import { LOGIN_ERROR_PARAM, ROUTES } from '../constants/routes';
import { getFieldErrors } from '../errors/apiError';
import { GoogleSignInLink } from '../components/GoogleSignInLink';
import { TextField } from '../components/TextField';

export function LoginPage() {
  const loginMutation = useLogin();
  const navigate = useNavigate();
  const location = useLocation();
  const fieldErrors = getFieldErrors(loginMutation.error);
  const [searchParams] = useSearchParams();
  const googleError = searchParams.get(LOGIN_ERROR_PARAM);

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
      <h1>Connexion</h1>
      {googleError !== null && (
        <p role="alert">{GOOGLE_ERROR_MESSAGES[googleError] ?? GOOGLE_GENERIC_ERROR_MESSAGE}</p>
      )}
      <form onSubmit={handleSubmit}>
        <TextField
          label="Email"
          name="email"
          type="email"
          autoComplete="email"
          required
          error={fieldErrors.email}
        />
        <TextField
          label="Mot de passe"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          maxLength={PASSWORD_MAX_LENGTH}
          error={fieldErrors.password}
        />
        {loginMutation.isError && <p role="alert">{loginMutation.error.message}</p>}
        <button type="submit" disabled={loginMutation.isPending}>
          {loginMutation.isPending ? 'Connexion…' : 'Se connecter'}
        </button>
      </form>
      <p>
        <GoogleSignInLink />
      </p>
      <p>
        Pas encore de compte ? <Link to={ROUTES.REGISTER}>Créer un compte</Link>
      </p>
    </main>
  );
}
