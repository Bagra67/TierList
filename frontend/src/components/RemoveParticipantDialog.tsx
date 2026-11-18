import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { type Participant, useRemoveParticipant } from '../api/rooms';
import { ConfirmMutationDialog } from './ConfirmMutationDialog';

interface RemoveParticipantDialogProps {
  code: string;
  participant: Participant;
}

export function RemoveParticipantDialog({ code, participant }: RemoveParticipantDialogProps) {
  const removeMutation = useRemoveParticipant(code);
  const [ban, setBan] = useState<boolean>(false);
  const { t } = useTranslation();
  const name: string = participant.display_name;

  return (
    <ConfirmMutationDialog
      openLabel={t('rooms.lobby.remove.open')}
      openAriaLabel={t('rooms.lobby.remove.openLabel', { name })}
      openVariant="outline"
      openSize="sm"
      title={t('rooms.lobby.remove.title', { name })}
      description={t('rooms.lobby.remove.warning')}
      cancelLabel={t('rooms.lobby.remove.cancel')}
      submitLabel={ban ? t('rooms.lobby.remove.submitBan') : t('rooms.lobby.remove.submit')}
      submittingLabel={t('rooms.lobby.remove.submitting')}
      mutation={removeMutation}
      confirm={() => removeMutation.mutateAsync({ participantId: participant.id, ban })}
      onClose={() => setBan(false)}
    >
      <label className="flex items-center gap-2">
        <input type="checkbox" checked={ban} onChange={(event) => setBan(event.target.checked)} />
        {t('rooms.lobby.remove.ban')}
      </label>
      {ban && participant.is_guest && (
        <p className="text-muted-foreground">{t('rooms.lobby.remove.guestWarning')}</p>
      )}
    </ConfirmMutationDialog>
  );
}
