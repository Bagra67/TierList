import { type QueryClient, useQueryClient } from '@tanstack/react-query';
import { type FormEvent, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { type NavigateFunction, useNavigate } from 'react-router';

import { useCloseRoom } from '../api/rooms';
import { canonicalRoomCode, roomQueryKey } from '../constants/rooms';
import { ROUTES } from '../constants/routes';
import { translateError } from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { DialogActions, ModalDialog } from './ModalDialog';
import { Button } from './ui/button';

interface CloseRoomDialogProps {
  code: string;
  // Une partie est en cours : elle sera close d'abord, le dialogue le dit
  gameInProgress: boolean;
}

// « Fermer la salle » (US-2.7), réservé au room admin : la salle est supprimée pour tous, d'où la
// confirmation dans un <dialog> natif (focus piégé, fermeture avec Échap)
export function CloseRoomDialog({ code, gameInProgress }: CloseRoomDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const closeMutation = useCloseRoom(code);
  const navigate: NavigateFunction = useNavigate();
  const queryClient: QueryClient = useQueryClient();
  const { t } = useTranslation();

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await closeMutation.mutateAsync();
    } catch {
      return; // l'erreur est affichée depuis closeMutation.error
    }
    // La salle n'existe plus : retour à l'accueil, puis la salle sort du cache (la relire
    // donnerait room_not_found)
    void navigate(ROUTES.HOME);
    queryClient.removeQueries({ queryKey: roomQueryKey(canonicalRoomCode(code)) });
  }

  return (
    <>
      <Button type="button" variant="destructive" onClick={() => dialogRef.current?.showModal()}>
        {t('rooms.lobby.close.open')}
      </Button>
      <ModalDialog
        dialogRef={dialogRef}
        title={t('rooms.lobby.close.title')}
        description={
          gameInProgress ? t('rooms.lobby.close.gameWarning') : t('rooms.lobby.close.warning')
        }
        onClose={() => closeMutation.reset()}
      >
        <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-4">
          {closeMutation.isError && (
            <ErrorMessage>{translateError(t, closeMutation.error)}</ErrorMessage>
          )}
          <DialogActions
            cancelLabel={t('rooms.lobby.close.cancel')}
            onCancel={() => dialogRef.current?.close()}
            submitLabel={
              closeMutation.isPending
                ? t('rooms.lobby.close.submitting')
                : t('rooms.lobby.close.submit')
            }
            submitVariant="destructive"
            submitDisabled={closeMutation.isPending}
          />
        </form>
      </ModalDialog>
    </>
  );
}
