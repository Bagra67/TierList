import { useEffect, useId, useRef, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router';

import { googleSignInUrl, useDeleteAccount, type User } from '../api/auth';
import { DELETE_ACCOUNT_STEP, PASSWORD_MAX_LENGTH } from '../constants/auth';
import { HTTP_STATUS } from '../constants/http';
import { ROUTES } from '../constants/routes';
import { ApiError, getFieldErrors, translateError, translateFieldError } from '../errors/apiError';
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
  const { t } = useTranslation();
  const fieldErrors = getFieldErrors(deleteMutation.error);
  // Un compte Google n'a pas de mot de passe : le backend exige alors une connexion récente,
  // et refuse (403) si elle date de trop longtemps.
  const needsGoogleSignIn =
    !user.has_password &&
    deleteMutation.error instanceof ApiError &&
    deleteMutation.error.status === HTTP_STATUS.FORBIDDEN;

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
    await navigate(ROUTES.LOGIN, { replace: true });
  }

  return (
    <>
      <button type="button" onClick={() => dialogRef.current?.showModal()}>
        {t('account.delete.open')}
      </button>
      <dialog ref={dialogRef} aria-labelledby={titleId} onClose={handleClose}>
        <h2 id={titleId}>{t('account.delete.title')}</h2>
        <p>{t('account.delete.warning')}</p>
        <form ref={formRef} onSubmit={handleSubmit}>
          {user.has_password ? (
            <TextField
              label={t('auth.password')}
              name="password"
              type="password"
              autoComplete="current-password"
              required
              maxLength={PASSWORD_MAX_LENGTH}
              error={translateFieldError(t, fieldErrors.password)}
            />
          ) : (
            <p>{t('account.delete.googleLinked')}</p>
          )}
          {deleteMutation.isError && <p role="alert">{translateError(t, deleteMutation.error)}</p>}
          {needsGoogleSignIn && (
            <p>
              <a href={googleSignInUrl(DELETE_ACCOUNT_STEP)}>
                {t('account.delete.signInAgainWithGoogle')}
              </a>
            </p>
          )}
          <button type="button" onClick={() => dialogRef.current?.close()}>
            {t('account.delete.cancel')}
          </button>{' '}
          <button type="submit" disabled={deleteMutation.isPending}>
            {deleteMutation.isPending ? t('account.delete.submitting') : t('account.delete.submit')}
          </button>
        </form>
      </dialog>
    </>
  );
}
