import { type FormEvent, useId } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';
import { type NavigateFunction, useNavigate } from 'react-router';

import { roomPath } from '../constants/routes';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';

// Champ « Rejoindre une salle » (US-2.4) : le code ouvre la salle, que l'utilisateur rejoint
// alors avec son compte. Un mauvais code est signalé par la page de la salle.
export function JoinRoomForm() {
  const codeId: string = useId();
  const navigate: NavigateFunction = useNavigate();
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const code: string = String(new FormData(event.currentTarget).get('code')).trim();
    if (code === '') return;
    await navigate(roomPath(code.toUpperCase()));
  }

  return (
    <form onSubmit={handleSubmit} className="flex w-full flex-col gap-2 rounded-xl border p-4">
      <h2 className="font-semibold">{t('home.joinRoom.title')}</h2>
      <Label htmlFor={codeId}>{t('home.joinRoom.code')}</Label>
      <div className="flex flex-wrap gap-2">
        <Input
          id={codeId}
          name="code"
          required
          autoComplete="off"
          className="flex-1 font-mono uppercase"
        />
        <Button type="submit">{t('home.joinRoom.submit')}</Button>
      </div>
    </form>
  );
}
