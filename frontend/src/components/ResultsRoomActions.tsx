import { useTranslation } from 'react-i18next';
import { type NavigateFunction, Link, useNavigate } from 'react-router';
import { cn } from 'cn';

import { useStartGame } from '../api/rooms';
import { type ResultsLinkState, roomPath } from '../constants/routes';
import { translateError } from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { Button } from './ui/button';
import { textLinkClassName } from './ui/text-link';

interface ResultsRoomActionsProps {
  fromRoom: ResultsLinkState;
}

export function ResultsRoomActions({ fromRoom }: ResultsRoomActionsProps) {
  const startMutation = useStartGame(fromRoom.roomCode);
  const navigate: NavigateFunction = useNavigate();
  const { t } = useTranslation();

  async function playAgain() {
    try {
      await startMutation.mutateAsync();
    } catch {
      return;
    }
    void navigate(roomPath(fromRoom.roomCode));
  }

  return (
    <div className="flex flex-col items-start gap-2">
      <div className="flex flex-wrap items-center gap-4">
        <Link to={roomPath(fromRoom.roomCode)} className={cn(textLinkClassName, 'text-sm')}>
          {t('results.backToRoom')}
        </Link>
        {fromRoom.isAdmin && (
          <Button type="button" disabled={startMutation.isPending} onClick={playAgain}>
            {startMutation.isPending ? t('results.playAgainSubmitting') : t('results.playAgain')}
          </Button>
        )}
      </div>
      {startMutation.isError && (
        <ErrorMessage>{translateError(t, startMutation.error)}</ErrorMessage>
      )}
    </div>
  );
}
