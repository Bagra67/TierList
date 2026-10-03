import { useId, useRef, type FormEvent } from 'react';
import { useNavigate } from 'react-router';

import { useDeleteAccount } from '../api/auth';
import { getFieldErrors } from '../api/client';
import { TextField } from './TextField';

// <dialog> natif ouvert avec showModal() : le navigateur piège le focus dedans et le ferme avec Échap
export function DeleteAccountDialog() {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const titleId = useId();
  const deleteMutation = useDeleteAccount();
  const navigate = useNavigate();
  const fieldErrors = getFieldErrors(deleteMutation.error);

  function handleClose() {
    formRef.current?.reset();
    deleteMutation.reset();
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await deleteMutation.mutateAsync({ password: String(form.get('password')) });
    } catch {
      return; // l'erreur est affichée depuis deleteMutation.error
    }
    dialogRef.current?.close();
    await navigate('/login', { replace: true });
  }

  return (
    <>
      <button type="button" onClick={() => dialogRef.current?.showModal()}>
        Supprimer mon compte
      </button>
      <dialog ref={dialogRef} aria-labelledby={titleId} onClose={handleClose}>
        <h2 id={titleId}>Supprimer mon compte</h2>
        <p>
          Cette action est définitive : votre compte et toutes ses données seront effacés. Saisissez
          votre mot de passe pour confirmer.
        </p>
        <form ref={formRef} onSubmit={handleSubmit}>
          <TextField
            label="Mot de passe"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            maxLength={128}
            error={fieldErrors.password}
          />
          {deleteMutation.isError && <p role="alert">{deleteMutation.error.message}</p>}
          <button type="button" onClick={() => dialogRef.current?.close()}>
            Annuler
          </button>{' '}
          <button type="submit" disabled={deleteMutation.isPending}>
            {deleteMutation.isPending ? 'Suppression…' : 'Supprimer définitivement'}
          </button>
        </form>
      </dialog>
    </>
  );
}
