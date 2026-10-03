import type { FormEvent } from 'react';
import { Link, useNavigate } from 'react-router';

import { useRegister } from '../api/auth';
import { getFieldErrors } from '../api/client';
import { TextField } from '../components/TextField';

export function RegisterPage() {
  const registerMutation = useRegister();
  const navigate = useNavigate();
  const fieldErrors = getFieldErrors(registerMutation.error);

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
    await navigate('/', { replace: true });
  }

  return (
    <main>
      <h1>Créer un compte</h1>
      <form onSubmit={handleSubmit}>
        <TextField
          label="Nom affiché"
          name="display_name"
          autoComplete="nickname"
          required
          maxLength={50}
          error={fieldErrors.display_name}
        />
        <TextField
          label="Email"
          name="email"
          type="email"
          autoComplete="email"
          required
          error={fieldErrors.email}
        />
        <TextField
          label="Mot de passe (8 caractères minimum)"
          name="password"
          type="password"
          autoComplete="new-password"
          required
          minLength={8}
          maxLength={128}
          error={fieldErrors.password}
        />
        {registerMutation.isError && <p role="alert">{registerMutation.error.message}</p>}
        <button type="submit" disabled={registerMutation.isPending}>
          {registerMutation.isPending ? 'Création…' : 'Créer mon compte'}
        </button>
      </form>
      <p>
        Déjà un compte ? <Link to="/login">Se connecter</Link>
      </p>
    </main>
  );
}
