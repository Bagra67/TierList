import { useTranslation } from 'react-i18next';

import { useEndCooldown } from '../api/rooms';
import { ConfirmMutationDialog } from './ConfirmMutationDialog';

interface EndCooldownDialogProps {
  code: string;
  onEnded: () => void;
}

export function EndCooldownDialog({ code, onEnded }: EndCooldownDialogProps) {
  const endMutation = useEndCooldown(code);
  const { t } = useTranslation();

  return (
    <ConfirmMutationDialog
      openLabel={t('rooms.game.cooldown.end.open')}
      openVariant="destructive"
      title={t('rooms.game.cooldown.end.title')}
      description={t('rooms.game.cooldown.end.warning')}
      cancelLabel={t('rooms.game.cooldown.end.cancel')}
      submitLabel={t('rooms.game.cooldown.end.submit')}
      submittingLabel={t('rooms.game.cooldown.end.submitting')}
      mutation={endMutation}
      confirm={() => endMutation.mutateAsync()}
      onConfirmed={onEnded}
    />
  );
}
