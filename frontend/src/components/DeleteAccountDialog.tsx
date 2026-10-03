import { useEffect, useId, useRef, type FormEvent } from 'react';
import { useNavigate } from 'react-router';

import { googleSignInUrl, useDeleteAccount, type User } from '../api/auth';
import { ApiError, getFieldErrors } from '../api/client';
import { TextField } from './TextField';

interface DeleteAccountDialogProps {
  user: User;
  // Ouvre le dialogue dès l'affichage : retour d'une reconnexion Google faite pour confirmer
  openOnMount?: boolean;
}

// <dialog> natif ouvert avec showModal() : le navigateur piège le focus dedans et le ferme avec Échap
export function DeleteAccountDialog({ user, openOnMount = false }: DeleteAccountDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const titleId = useId();
  const deleteMutation = useDeleteAccount();
  const navigate = useNavigate();
  const fieldErrors = getFieldErrors(deleteMutation.error);
  // Un compte Google n'a pas de mot de passe : le backend exige alors une connexion récente,
  // et refuse (403) si elle date de trop longtemps.
  const needsGoogleSignIn =
    !user.has_password &&
    deleteMutation.error instanceof ApiError &&
    deleteMutation.error.status === 403;

  useEffect(() => {
    const dialog = dialogRef.current;
    // Synchronise l'élément DOM : showModal() échoue sur un dialogue déjà ouvert
    if (openOnMount && dialog !== null && !dialog.open) {
      dialog.showModal();
    }
  }, [openOnMount]);

  function handleClose() {
    formRef.current?.reset();
    deleteMutation.reset();
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const password = new FormData(event.currentTarget).get('password');
    try {
      await deleteMutation.mutateAsync(password === null ? {} : { password: String(password) });
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
        <p>Cette action est définitive : votre compte et toutes ses données seront effacés.</p>
        <form ref={formRef} onSubmit={handleSubmit}>
          {user.has_password ? (
            <TextField
              label="Mot de passe"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              maxLength={128}
              error={fieldErrors.password}
            />
          ) : (
            <p>Votre compte est relié à Google : aucune saisie n'est nécessaire.</p>
          )}
          {deleteMutation.isError && <p role="alert">{deleteMutation.error.message}</p>}
          {needsGoogleSignIn && (
            <p>
              <a href={googleSignInUrl('delete-account')}>Se reconnecter avec Google</a>
            </p>
          )}
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
