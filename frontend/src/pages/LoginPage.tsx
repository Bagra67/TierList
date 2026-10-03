import type { FormEvent } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router';

import { useLogin } from '../api/auth';
import { getFieldErrors } from '../api/client';
import { GoogleSignInLink } from '../components/GoogleSignInLink';
import { TextField } from '../components/TextField';

// Codes d'erreur du retour de Google (backend : /auth/google/callback → /login?error=<code>)
const GOOGLE_ERROR_MESSAGES: Record<string, string> = {
  google_cancelled: 'Connexion avec Google annulée.',
  google_email_not_verified:
    "Votre adresse Google n'est pas vérifiée : elle ne peut pas servir à vous connecter.",
  google_unavailable: "La connexion avec Google n'est pas disponible pour le moment.",
  google_failed: 'La connexion avec Google a échoué, veuillez réessayer.',
};

export function LoginPage() {
  const loginMutation = useLogin();
  const navigate = useNavigate();
  const location = useLocation();
  const fieldErrors = getFieldErrors(loginMutation.error);
  const [searchParams] = useSearchParams();
  const googleError = searchParams.get('error');

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
    const from = (location.state as { from?: string } | null)?.from ?? '/';
    await navigate(from, { replace: true });
  }

  return (
    <main>
      <h1>Connexion</h1>
      {googleError !== null && (
        <p role="alert">
          {GOOGLE_ERROR_MESSAGES[googleError] ?? GOOGLE_ERROR_MESSAGES.google_failed}
        </p>
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
          maxLength={128}
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
        Pas encore de compte ? <Link to="/register">Créer un compte</Link>
      </p>
    </main>
  );
}
