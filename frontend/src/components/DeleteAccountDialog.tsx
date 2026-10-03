import { useEffect, useId, useRef, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router';

import { googleSignInUrl, useDeleteAccount, type User } from '../api/auth';
import { DELETE_ACCOUNT_STEP, PASSWORD_MAX_LENGTH } from '../constants/auth';
import { HTTP_STATUS } from '../constants/http';
import { ROUTES } from '../constants/routes';
import { ApiError, getFieldErrors, translateError, translateFieldError } from '../errors/apiError';
import { TextField } from './TextField';
import { Button } from './ui/button';

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
      <Button type="button" variant="destructive" onClick={() => dialogRef.current?.showModal()}>
        {t('account.delete.open')}
      </Button>
      <dialog
        ref={dialogRef}
        aria-labelledby={titleId}
        onClose={handleClose}
        className="m-auto w-full max-w-md rounded-xl bg-card p-6 text-sm text-card-foreground shadow-lg ring-1 ring-foreground/10 backdrop:bg-black/50"
      >
        <h2 id={titleId} className="text-lg font-semibold">
          {t('account.delete.title')}
        </h2>
        <p className="mt-2 text-muted-foreground">{t('account.delete.warning')}</p>
        <form ref={formRef} onSubmit={handleSubmit} className="mt-4 flex flex-col gap-4">
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
          {deleteMutation.isError && (
            <p role="alert" className="text-destructive">
              {translateError(t, deleteMutation.error)}
            </p>
          )}
          {needsGoogleSignIn && (
            <p>
              <a
                href={googleSignInUrl(DELETE_ACCOUNT_STEP)}
                className="font-medium underline underline-offset-4"
              >
                {t('account.delete.signInAgainWithGoogle')}
              </a>
            </p>
          )}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => dialogRef.current?.close()}>
              {t('account.delete.cancel')}
            </Button>
            <Button type="submit" variant="destructive" disabled={deleteMutation.isPending}>
              {deleteMutation.isPending
                ? t('account.delete.submitting')
                : t('account.delete.submit')}
            </Button>
          </div>
        </form>
      </dialog>
    </>
  );
}
