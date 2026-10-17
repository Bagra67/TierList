import { useTranslation } from 'react-i18next';

import { useStartGame } from '../api/rooms';
import { translateError } from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { Button } from './ui/button';

interface StartGameButtonProps {
  code: string;
}

// Lance une partie (US-3.1), pour le room admin hors partie. Sans confirmation : rien n'est
// détruit, et le premier item s'affiche aussitôt chez tous les participants.
export function StartGameButton({ code }: StartGameButtonProps) {
  const startMutation = useStartGame(code);
  const { t } = useTranslation();

  return (
    <div className="flex flex-col items-start gap-2">
      <Button
        type="button"
        disabled={startMutation.isPending}
        onClick={() => startMutation.mutate()}
      >
        {startMutation.isPending
          ? t('rooms.lobby.start.submitting')
          : t('rooms.lobby.start.submit')}
      </Button>
      {startMutation.isError && (
        <ErrorMessage>{translateError(t, startMutation.error)}</ErrorMessage>
      )}
    </div>
  );
}
