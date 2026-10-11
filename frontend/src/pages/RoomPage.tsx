import type { UseQueryResult } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
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
import { type GuestRoom, type Room, type RoomViewer, useRoom } from '../api/rooms';
import { ErrorMessage } from '../components/ErrorMessage';
import { GuestLinkNotice } from '../components/GuestLinkNotice';
import { JoinRoomScreen } from '../components/JoinRoomScreen';
import { RoomLobby } from '../components/RoomLobby';
import { GUEST_LINK_FRAGMENT } from '../constants/rooms';
import { ApiError, translateError } from '../errors/apiError';

// Jeton du lien perso d'un invité (#guest=<jeton>), absent d'un lien ordinaire
function guestTokenFrom(hash: string): string | null {
  const token: string | null = new URLSearchParams(hash.replace(/^#/, '')).get(GUEST_LINK_FRAGMENT);
  return token === '' ? null : token;
}

// Page d'une salle, ouverte par son lien ou son code. Un compte connecté y entre comme joueur
// (US-2.4). Sans compte, le navigateur d'un invité est reconnu par son cookie, ou par son lien
// perso (US-5.4) ; un nouveau venu choisit de se connecter ou d'entrer en invité (US-2.5). Pas
// encore de mise à jour en direct (#85) : la salle est relue quand on revient sur l'onglet.
export function RoomPage() {
  // Toujours présent : la route ROOM déclare ce paramètre
  const { code = '' }: Readonly<Params> = useParams();
  const location: Location = useLocation();
  const navigate: NavigateFunction = useNavigate();
  const { data: user, isPending: isUserPending } = useCurrentUser();
  const viewer: RoomViewer | undefined = isUserPending
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
  // Lien perso de l'invité qui vient d'entrer : affiché une fois, il n'est pas relu ensuite
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

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-col items-start gap-6 px-4 py-10">
      {isPending && error === null && (
        <p className="text-muted-foreground">{t('common.loading')}</p>
      )}
      {showError && <ErrorMessage>{translateError(t, error)}</ErrorMessage>}
      {canJoinAsGuest && <JoinRoomScreen code={code} onJoinedAsGuest={setGuestRoom} />}
      {guestRoom !== null && room !== undefined && <GuestLinkNotice guestRoom={guestRoom} />}
      {room !== undefined && <RoomLobby room={room} />}
    </main>
  );
}
