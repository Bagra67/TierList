import type { FormEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router';

import { useLogin } from '../api/auth';
import { getFieldErrors } from '../api/client';
import { TextField } from '../components/TextField';

export function LoginPage() {
  const loginMutation = useLogin();
  const navigate = useNavigate();
  const location = useLocation();
  const fieldErrors = getFieldErrors(loginMutation.error);

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
        Pas encore de compte ? <Link to="/register">Créer un compte</Link>
      </p>
    </main>
  );
}
