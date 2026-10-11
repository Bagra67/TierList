import type { FormEvent } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';
import { type Location, Link, useLocation } from 'react-router';

import { type GuestRoom, useJoinAsGuest } from '../api/rooms';
import { signInRedirectState } from '../auth/signInRedirect';
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

interface JoinRoomScreenProps {
  code: string;
  onJoinedAsGuest: (guestRoom: GuestRoom) => void;
}

// Écran de qui ouvre le lien d'une salle sans compte connecté ni place (US-2.4, US-2.5) : se
// connecter pour revenir ici avec son compte, ou entrer tout de suite en invité avec un pseudo
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
      return; // l'erreur est affichée depuis joinMutation.error
    }
    onJoinedAsGuest(guestRoom);
  }

  return (
    <>
      <h1 className="text-2xl font-semibold">{t('rooms.join.title')}</h1>
      <div className="flex flex-col gap-1">
        <h2 className="text-sm text-muted-foreground">{t('rooms.lobby.code')}</h2>
        <p className="font-mono text-3xl font-semibold tracking-widest">{code.toUpperCase()}</p>
      </div>
      <section className="flex w-full flex-col items-start gap-2 rounded-xl border p-4">
        <h2 className="font-semibold">{t('rooms.join.withAccount')}</h2>
        <p className="text-sm text-muted-foreground">{t('rooms.join.withAccountHint')}</p>
        {/* Après la connexion, retour sur cette salle (RequireAuth fait de même) */}
        <Button asChild variant="outline">
          <Link to={ROUTES.LOGIN} state={signInRedirectState(location)}>
            {t('rooms.join.signIn')}
          </Link>
        </Button>
      </section>
      <section className="flex w-full flex-col gap-2 rounded-xl border p-4">
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
          {/* Pseudo déjà pris, salle introuvable… ; une erreur du champ est déjà sous lui */}
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
