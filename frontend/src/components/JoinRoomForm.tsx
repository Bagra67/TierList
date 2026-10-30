import { cn } from 'cn';
import { type FormEvent, useId } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';
import { type NavigateFunction, useNavigate } from 'react-router';

import { canonicalRoomCode } from '../constants/rooms';
import { roomPath } from '../constants/routes';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';

// Champ « Rejoindre une salle » (US-2.4) : le code ouvre la salle, que l'utilisateur rejoint
// alors avec son compte, ou en invité sans compte. Un mauvais code est signalé par la page de la
// salle. Sur l'accueil, c'est l'action principale : un grand champ, en lettres espacées comme le
// code affiché dans la salle
export function JoinRoomForm({ className }: { className?: string }) {
  const codeId: string = useId();
  const navigate: NavigateFunction = useNavigate();
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const code: string = canonicalRoomCode(String(new FormData(event.currentTarget).get('code')));
    if (code === '') return;
    await navigate(roomPath(code));
  }

  return (
    <form onSubmit={handleSubmit} className={cn('flex w-full flex-col gap-2', className)}>
      <h2 className="text-base font-semibold">{t('home.joinRoom.title')}</h2>
      {/* Le titre dit déjà l'action : le label reste pour les lecteurs d'écran, et la même phrase
          s'affiche dans le champ vide */}
      <Label htmlFor={codeId} className="sr-only">
        {t('home.joinRoom.code')}
      </Label>
      <div className="flex flex-wrap gap-2">
        <Input
          id={codeId}
          name="code"
          required
          autoComplete="off"
          placeholder={t('home.joinRoom.code')}
          className="h-12 placeholder:font-sans placeholder:text-base placeholder:tracking-normal placeholder:normal-case min-w-0 flex-1 font-mono text-xl tracking-[0.3em] uppercase md:text-xl"
        />
        <Button type="submit" size="lg" className="h-12 px-6">
          {t('home.joinRoom.submit')}
        </Button>
      </div>
    </form>
  );
}
