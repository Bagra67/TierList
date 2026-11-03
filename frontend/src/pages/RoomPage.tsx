import { type QueryClient, type UseQueryResult, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useState } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';
import {
  type Location,
  type NavigateFunction,
  type Params,
  useLocation,
  useNavigate,
  Link,
  useParams,
} from 'react-router';

import { useCurrentUser } from '../api/auth';
import { type RemovalReason, type RoomEventsState, useRoomEvents } from '../api/roomChannel';
import { type GuestRoom, type Room, type RoomViewer, useRoom } from '../api/rooms';
import { ErrorMessage } from '../components/ErrorMessage';
import { GuestLinkSection } from '../components/GuestLinkSection';
import { JoinRoomScreen } from '../components/JoinRoomScreen';
import { RoomLobby } from '../components/RoomLobby';
import { Button } from '../components/ui/button';
import { canonicalRoomCode, GUEST_LINK_FRAGMENT, roomQueryKey } from '../constants/rooms';
import { ROUTES } from '../constants/routes';
import { ApiError, translateError } from '../errors/apiError';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { PageContainer } from '../components/PageContainer';

function guestTokenFrom(hash: string): string | null {
  const token: string | null = new URLSearchParams(hash.replace(/^#/, '')).get(GUEST_LINK_FRAGMENT);
  return token === '' ? null : token;
}

interface Removal {
  roomCode: string;
  reason: RemovalReason;
}

const REMOVAL_MESSAGES = {
  removed: 'rooms.lobby.removed',
  banned: 'rooms.lobby.banned',
  closed: 'rooms.lobby.closed',
} as const satisfies Record<RemovalReason, string>;

export function RoomPage() {
  const { code = '' }: Readonly<Params> = useParams();
  const location: Location = useLocation();
  const navigate: NavigateFunction = useNavigate();
  const queryClient: QueryClient = useQueryClient();
  const { data: user, isPending: isUserPending } = useCurrentUser();
  const [lastRemoval, setLastRemoval] = useState<Removal | null>(null);
  // Un retrait ne vaut que pour sa salle : en ouvrir une autre l'oublie
  const removal: Removal | null =
    lastRemoval?.roomCode === canonicalRoomCode(code) ? lastRemoval : null;
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
    (reason: RemovalReason) => {
      const roomCode: string = canonicalRoomCode(code);
      setLastRemoval({ roomCode, reason });
      queryClient.removeQueries({ queryKey: roomQueryKey(roomCode) });
    },
    [code, queryClient],
  );
  const viewerHasSeat: boolean = room !== undefined;
  const roomEvents: RoomEventsState = useRoomEvents(code, viewer, viewerHasSeat, handleRemoved);
  const [justIssuedGuestLink, setJustIssuedGuestLink] = useState<GuestRoom | null>(null);
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();

  useEffect(() => {
    if (guestToken !== null && isSuccess) {
      void navigate({ pathname: location.pathname, hash: '' }, { replace: true });
    }
  }, [guestToken, isSuccess, location.pathname, navigate]);

  const errorCode: string | undefined = error instanceof ApiError ? error.code : undefined;
  const visitorHasNoSeatYet: boolean = viewer === 'guest' && errorCode === 'room_not_found';
  const canJoinAsGuest: boolean =
    visitorHasNoSeatYet || (viewer === 'guest' && errorCode === 'guest_link_invalid');
  const showError: boolean = error !== null && !visitorHasNoSeatYet;

  if (removal !== null) {
    return (
      <PageContainer width="app" className="flex flex-col items-start gap-6">
        <p role="status" className="font-medium">
          {t(REMOVAL_MESSAGES[removal.reason])}
        </p>
        {removal.reason === 'removed' ? (
          <Button type="button" onClick={() => setLastRemoval(null)}>
            {t('rooms.lobby.comeBack')}
          </Button>
        ) : (
          <Button asChild variant="outline">
            <Link to={ROUTES.HOME}>{t('rooms.lobby.backHome')}</Link>
          </Button>
        )}
      </PageContainer>
    );
  }

  return (
    <PageContainer width="app" className="flex flex-col items-start gap-6">
      {isPending && error === null && <LoadingSkeleton shape="board" />}
      {showError && <ErrorMessage>{translateError(t, error)}</ErrorMessage>}
      {canJoinAsGuest && <JoinRoomScreen code={code} onJoinedAsGuest={setJustIssuedGuestLink} />}
      {viewer === 'guest' && room !== undefined && (
        <GuestLinkSection
          code={code}
          justIssuedGuestLink={justIssuedGuestLink}
          onRenewed={setJustIssuedGuestLink}
        />
      )}
      {room !== undefined && roomEvents.unavailable && (
        <p
          role="status"
          className="w-full rounded-lg border border-warning bg-warning/15 px-3 py-2 text-sm"
        >
          {t('rooms.lobby.liveUnavailable')}
        </p>
      )}
      {room !== undefined && <RoomLobby room={room} />}
    </PageContainer>
  );
}
