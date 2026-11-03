import { type UseTranslationResponse, useTranslation } from 'react-i18next';
import { type NavigateFunction, useNavigate } from 'react-router';

import { type Room, useCreateRoom } from '../api/rooms';
import { roomPath } from '../constants/routes';
import { translateError } from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { Button } from './ui/button';

interface CreateRoomButtonProps {
  templateId: string;
  templateName: string;
}

export function CreateRoomButton({ templateId, templateName }: CreateRoomButtonProps) {
  const createMutation = useCreateRoom();
  const navigate: NavigateFunction = useNavigate();
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();

  async function handleClick() {
    let room: Room;
    try {
      room = await createMutation.mutateAsync({ template_id: templateId });
    } catch {
      return;
    }
    await navigate(roomPath(room.code));
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <Button
        type="button"
        aria-label={t('rooms.create.openLabel', { name: templateName })}
        disabled={createMutation.isPending}
        onClick={handleClick}
      >
        {createMutation.isPending ? t('rooms.create.submitting') : t('rooms.create.open')}
      </Button>
      {createMutation.isError && (
        <ErrorMessage className="text-sm">{translateError(t, createMutation.error)}</ErrorMessage>
      )}
    </div>
  );
}
