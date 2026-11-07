import { useTranslation } from 'react-i18next';

import { useStartGame } from '../api/rooms';
import { translateError } from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { Button } from './ui/button';

interface StartGameButtonProps {
  code: string;
  replay: boolean;
}

export function StartGameButton({ code, replay }: StartGameButtonProps) {
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
          : replay
            ? t('rooms.lobby.start.replay')
            : t('rooms.lobby.start.submit')}
      </Button>
      {startMutation.isError && (
        <ErrorMessage>{translateError(t, startMutation.error)}</ErrorMessage>
      )}
    </div>
  );
}
