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
  // La salle d'où viennent les résultats (état de navigation posé par le lobby)
  fromRoom: ResultsLinkState;
}

// Sur les résultats ouverts depuis le lobby : revenir à la salle, et pour le room admin rejouer
// (US-2.9). Le serveur vérifie lui-même le rôle : le bouton n'est qu'un raccourci. Un visiteur du
// lien public n'a pas de salle, il ne voit rien de tout ça
export function ResultsRoomActions({ fromRoom }: ResultsRoomActionsProps) {
  const startMutation = useStartGame(fromRoom.roomCode);
  const navigate: NavigateFunction = useNavigate();
  const { t } = useTranslation();

  async function playAgain() {
    try {
      await startMutation.mutateAsync();
    } catch {
      return; // l'erreur est affichée depuis startMutation.error
    }
    // La salle renvoyée porte la nouvelle partie : son écran de jeu s'affiche dans le lobby
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
