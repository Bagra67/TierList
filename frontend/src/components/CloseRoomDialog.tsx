import { type QueryClient, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { type NavigateFunction, useNavigate } from 'react-router';

import { useCloseRoom } from '../api/rooms';
import { canonicalRoomCode, roomQueryKey } from '../constants/rooms';
import { ROUTES } from '../constants/routes';
import { ConfirmMutationDialog } from './ConfirmMutationDialog';

interface CloseRoomDialogProps {
  code: string;
  gameInProgress: boolean;
}

export function CloseRoomDialog({ code, gameInProgress }: CloseRoomDialogProps) {
  const closeMutation = useCloseRoom(code);
  const navigate: NavigateFunction = useNavigate();
  const queryClient: QueryClient = useQueryClient();
  const { t } = useTranslation();

  function leaveClosedRoom() {
    void navigate(ROUTES.HOME);
    queryClient.removeQueries({ queryKey: roomQueryKey(canonicalRoomCode(code)) });
  }

  return (
    <ConfirmMutationDialog
      openLabel={t('rooms.lobby.close.open')}
      openVariant="destructive"
      title={t('rooms.lobby.close.title')}
      description={
        gameInProgress ? t('rooms.lobby.close.gameWarning') : t('rooms.lobby.close.warning')
      }
      cancelLabel={t('rooms.lobby.close.cancel')}
      submitLabel={t('rooms.lobby.close.submit')}
      submittingLabel={t('rooms.lobby.close.submitting')}
      mutation={closeMutation}
      confirm={() => closeMutation.mutateAsync()}
      onConfirmed={leaveClosedRoom}
    />
  );
}
