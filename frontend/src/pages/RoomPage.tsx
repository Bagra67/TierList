import { type QueryClient, type UseQueryResult, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useState } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';
import {
  type Location,
  type NavigateFunction,
  type Params,
  useLocation,
  useNavigate,
  useParams,
} from 'react-router';

import { useCurrentUser } from '../api/auth';
import { type RoomEventsState, useRoomEvents } from '../api/roomChannel';
import { type GuestRoom, type Room, type RoomViewer, useRoom } from '../api/rooms';
import { ErrorMessage } from '../components/ErrorMessage';
import { GuestLinkSection } from '../components/GuestLinkSection';
import { JoinRoomScreen } from '../components/JoinRoomScreen';
import { RoomLobby } from '../components/RoomLobby';
import { Button } from '../components/ui/button';
import { canonicalRoomCode, GUEST_LINK_FRAGMENT, roomQueryKey } from '../constants/rooms';
import { ApiError, translateError } from '../errors/apiError';

// Jeton du lien perso d'un invité (#guest=<jeton>), absent d'un lien ordinaire
function guestTokenFrom(hash: string): string | null {
  const token: string | null = new URLSearchParams(hash.replace(/^#/, '')).get(GUEST_LINK_FRAGMENT);
  return token === '' ? null : token;
}

// Le room admin a retiré le lecteur de cette salle (banned : il l'a aussi banni)
interface Removal {
  roomCode: string;
  banned: boolean;
}

// Page d'une salle, ouverte par son lien ou son code. Un compte connecté y entre comme joueur
// (US-2.4). Sans compte, le navigateur d'un invité est reconnu par son cookie, ou par son lien
// perso (US-5.4) ; un nouveau venu choisit de se connecter ou d'entrer en invité (US-2.5). Une fois
// la salle chargée, son canal temps réel la tient à jour (arrivées, départs, réglages, présence).
// Retiré par le room admin (US-2.11), le lecteur en est prévenu et la salle n'est plus lue : une
// relecture ferait rejoindre à nouveau un compte sans qu'il l'ait demandé.
export function RoomPage() {
  // Toujours présent : la route ROOM déclare ce paramètre
  const { code = '' }: Readonly<Params> = useParams();
  const location: Location = useLocation();
  const navigate: NavigateFunction = useNavigate();
  const queryClient: QueryClient = useQueryClient();
  const { data: user, isPending: isUserPending } = useCurrentUser();
  const [lastRemoval, setLastRemoval] = useState<Removal | null>(null);
  // Un retrait ne vaut que pour sa salle : en ouvrir une autre l'oublie
  const removal: Removal | null =
    lastRemoval?.roomCode === canonicalRoomCode(code) ? lastRemoval : null;
  // Sans lecteur, la salle n'est ni lue ni suivie (undefined : session en attente, ou retiré)
  const viewer: RoomViewer | undefined =
    isUserPending || removal !== null
      ? undefined
      : user !== null && user !== undefined
        ? 'account'
        : 'guest';
  const guestToken: string | null = viewer === 'guest' ? guestTokenFrom(location.hash) : null;
  const {
    data: room,
    isPending,
    isSuccess,
    error,
  }: UseQueryResult<Room> = useRoom(code, viewer, guestToken);
  const handleRemoved = useCallback(
    (banned: boolean) => {
      const roomCode: string = canonicalRoomCode(code);
      setLastRemoval({ roomCode, banned });
      // Sa place n'existe plus : la salle en cache ne le concerne plus
      queryClient.removeQueries({ queryKey: roomQueryKey(roomCode) });
    },
    [code, queryClient],
  );
  // Ouvert dès que le lecteur a une place : la salle est chargée
  const roomEvents: RoomEventsState = useRoomEvents(
    code,
    viewer,
    room !== undefined,
    handleRemoved,
  );
  // Lien perso de l'invité qui vient d'entrer (ou de le renouveler) : il n'est pas relu ensuite
  const [guestRoom, setGuestRoom] = useState<GuestRoom | null>(null);
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();

  // Le jeton du lien perso a servi (le cookie est posé) : il sort de l'adresse, pour ne pas
  // rester dans l'historique ni se montrer à l'écran
  useEffect(() => {
    if (guestToken !== null && isSuccess) {
      void navigate({ pathname: location.pathname, hash: '' }, { replace: true });
    }
  }, [guestToken, isSuccess, location.pathname, navigate]);

  // Sans place : un visiteur sans compte peut rejoindre ; lien perso expiré ou salle fermée,
  // il est prévenu, puis peut entrer à nouveau en invité
  const errorCode: string | undefined = error instanceof ApiError ? error.code : undefined;
  const canJoinAsGuest: boolean =
    viewer === 'guest' && (errorCode === 'room_not_found' || errorCode === 'guest_link_invalid');
  // Pour un visiteur, room_not_found veut seulement dire « pas encore de place » : pas d'erreur
  const showError: boolean =
    error !== null && !(viewer === 'guest' && errorCode === 'room_not_found');

  if (removal !== null) {
    return (
      <main className="mx-auto flex w-full max-w-2xl flex-col items-start gap-6 px-4 py-10">
        <p role="status" className="font-medium">
          {removal.banned ? t('rooms.lobby.banned') : t('rooms.lobby.removed')}
        </p>
        {/* Un banni serait refusé : seul un participant retiré peut revenir */}
        {!removal.banned && (
          <Button type="button" onClick={() => setLastRemoval(null)}>
            {t('rooms.lobby.comeBack')}
          </Button>
        )}
      </main>
    );
  }

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-col items-start gap-6 px-4 py-10">
      {isPending && error === null && (
        <p className="text-muted-foreground">{t('common.loading')}</p>
      )}
      {showError && <ErrorMessage>{translateError(t, error)}</ErrorMessage>}
      {canJoinAsGuest && <JoinRoomScreen code={code} onJoinedAsGuest={setGuestRoom} />}
      {viewer === 'guest' && room !== undefined && (
        <GuestLinkSection code={code} guestRoom={guestRoom} onRenewed={setGuestRoom} />
      )}
      {room !== undefined && roomEvents.unavailable && (
        <p role="status" className="text-sm text-muted-foreground">
          {t('rooms.lobby.liveUnavailable')}
        </p>
      )}
      {room !== undefined && <RoomLobby room={room} />}
    </main>
  );
}
