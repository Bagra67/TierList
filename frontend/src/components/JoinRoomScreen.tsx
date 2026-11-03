import type { FormEvent } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';
import { type Location, Link, useLocation } from 'react-router';

import { type GuestRoom, useJoinAsGuest } from '../api/rooms';
import { signInRedirectState } from '../auth/signInRedirect';
import { canonicalRoomCode } from '../constants/rooms';
import { ROUTES } from '../constants/routes';
import {
  type FieldError,
  getFieldErrors,
  translateError,
  translateFieldError,
} from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { TextField } from './TextField';
import { Button } from './ui/button';
import { panelVariants } from './ui/panel';
import { cn } from 'cn';

interface JoinRoomScreenProps {
  code: string;
  onJoinedAsGuest: (guestRoom: GuestRoom) => void;
}

export function JoinRoomScreen({ code, onJoinedAsGuest }: JoinRoomScreenProps) {
  const location: Location = useLocation();
  const joinMutation = useJoinAsGuest(code);
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const fieldErrors: Record<string, FieldError> = getFieldErrors(joinMutation.error);
  const nicknameError: string | undefined = translateFieldError(t, fieldErrors.nickname);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nickname: string = String(new FormData(event.currentTarget).get('nickname'));
    let guestRoom: GuestRoom;
    try {
      guestRoom = await joinMutation.mutateAsync({ nickname });
    } catch {
      return;
    }
    onJoinedAsGuest(guestRoom);
  }

  return (
    <>
      <h1 className="text-2xl font-semibold">{t('rooms.join.title')}</h1>
      <div className="flex flex-col gap-1">
        <h2 className="text-sm text-muted-foreground">{t('rooms.lobby.code')}</h2>
        <p className="font-mono text-3xl font-semibold tracking-widest">
          {canonicalRoomCode(code)}
        </p>
      </div>
      <section className={cn(panelVariants(), 'items-start')}>
        <h2 className="font-semibold">{t('rooms.join.withAccount')}</h2>
        <p className="text-sm text-muted-foreground">{t('rooms.join.withAccountHint')}</p>
        <Button asChild variant="outline">
          <Link to={ROUTES.LOGIN} state={signInRedirectState(location)}>
            {t('rooms.join.signIn')}
          </Link>
        </Button>
      </section>
      <section className={panelVariants()}>
        <h2 className="font-semibold">{t('rooms.join.asGuest')}</h2>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <TextField
            label={t('rooms.join.nickname')}
            name="nickname"
            required
            autoComplete="nickname"
            error={nicknameError}
          />
          <p className="text-sm text-muted-foreground">{t('rooms.join.asGuestHint')}</p>
          {joinMutation.isError && nicknameError === undefined && (
            <ErrorMessage>{translateError(t, joinMutation.error)}</ErrorMessage>
          )}
          <Button type="submit" className="self-start" disabled={joinMutation.isPending}>
            {joinMutation.isPending ? t('rooms.join.submitting') : t('rooms.join.submit')}
          </Button>
        </form>
      </section>
    </>
  );
}
