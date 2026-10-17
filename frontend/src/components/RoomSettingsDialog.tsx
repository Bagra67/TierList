import { type FormEvent, useRef, useState } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import {
  type AutoAdvance,
  type ItemOrder,
  type Room,
  type RoomSettingsChanges,
  useUpdateRoomSettings,
} from '../api/rooms';
import {
  type FieldError,
  getFieldErrors,
  translateError,
  translateFieldError,
} from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { DialogActions, ModalDialog } from './ModalDialog';
import { TextField } from './TextField';
import { Button } from './ui/button';

const ITEM_ORDERS: readonly ItemOrder[] = ['template', 'random'];
const AUTO_ADVANCES: readonly AutoAdvance[] = ['none', 'timer', 'everyone_placed'];

interface RoomSettingsDialogProps {
  room: Room;
}

// Réglages de la prochaine partie (US-2.2), réservés au room admin, dans un <dialog> natif
// (focus piégé, fermeture avec Échap)
export function RoomSettingsDialog({ room }: RoomSettingsDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const settingsMutation: SettingsMutation = useUpdateRoomSettings(room.code);
  const [formVersion, setFormVersion] = useState<number>(0);
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();

  // Le formulaire repart des réglages actuels à chaque ouverture (ils ont pu changer depuis)
  function handleOpen() {
    setFormVersion((version) => version + 1);
    dialogRef.current?.showModal();
  }

  return (
    <>
      <Button type="button" variant="outline" onClick={handleOpen}>
        {t('rooms.settings.edit')}
      </Button>
      <ModalDialog
        dialogRef={dialogRef}
        title={t('rooms.settings.dialogTitle')}
        onClose={() => settingsMutation.reset()}
      >
        {/* Une nouvelle clé remonte le formulaire : ses champs reprennent les réglages actuels */}
        <RoomSettingsForm
          key={formVersion}
          room={room}
          settingsMutation={settingsMutation}
          onSaved={() => dialogRef.current?.close()}
          onCancel={() => dialogRef.current?.close()}
        />
      </ModalDialog>
    </>
  );
}

type SettingsMutation = ReturnType<typeof useUpdateRoomSettings>;

interface RoomSettingsFormProps {
  room: Room;
  settingsMutation: SettingsMutation;
  onSaved: () => void;
  onCancel: () => void;
}

// Pendant une partie, seules les arrivées restent modifiables (US-2.10). Les bornes des durées ne
// sont pas recopiées : le backend les renvoie dans ses erreurs (« Au moins 5. »).
function RoomSettingsForm({ room, settingsMutation, onSaved, onCancel }: RoomSettingsFormProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  // Suivi pour activer la durée du timer seulement quand le timer est choisi
  const [autoAdvance, setAutoAdvance] = useState<AutoAdvance>(room.settings.auto_advance);
  const isPlaying: boolean = room.status === 'playing';
  const fieldErrors: Record<string, FieldError> = getFieldErrors(settingsMutation.error);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData: FormData = new FormData(event.currentTarget);
    const lateArrivalsAllowed: boolean = formData.get('late_arrivals_allowed') === 'on';
    // Un champ désactivé n'est pas dans formData : la durée du timer n'est envoyée qu'avec le
    // timer, et pendant une partie seules les arrivées le sont
    const timerSeconds: FormDataEntryValue | null = formData.get('timer_seconds');
    const changes: RoomSettingsChanges = isPlaying
      ? { late_arrivals_allowed: lateArrivalsAllowed }
      : {
          item_order: formData.get('item_order') as ItemOrder,
          auto_advance: formData.get('auto_advance') as AutoAdvance,
          ...(timerSeconds !== null && { timer_seconds: Number(timerSeconds) }),
          cooldown_seconds: Number(formData.get('cooldown_seconds')),
          admin_plays: formData.get('admin_plays') === 'on',
          late_arrivals_allowed: lateArrivalsAllowed,
        };
    try {
      await settingsMutation.mutateAsync(changes);
    } catch {
      return; // l'erreur est affichée depuis settingsMutation.error
    }
    onSaved();
  }

  return (
    <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-5">
      {isPlaying && <p className="text-muted-foreground">{t('rooms.settings.lockedNote')}</p>}
      <fieldset disabled={isPlaying} className="flex flex-col gap-2">
        <legend className="mb-2 font-medium">{t('rooms.settings.itemOrder.label')}</legend>
        {ITEM_ORDERS.map((itemOrder) => (
          <label key={itemOrder} className="flex items-center gap-2">
            <input
              type="radio"
              name="item_order"
              value={itemOrder}
              defaultChecked={room.settings.item_order === itemOrder}
            />
            {t(`rooms.settings.itemOrder.${itemOrder}`)}
          </label>
        ))}
      </fieldset>
      <fieldset disabled={isPlaying} className="flex flex-col gap-2">
        <legend className="mb-2 font-medium">{t('rooms.settings.autoAdvance.label')}</legend>
        {AUTO_ADVANCES.map((option) => (
          <label key={option} className="flex items-center gap-2">
            <input
              type="radio"
              name="auto_advance"
              value={option}
              defaultChecked={room.settings.auto_advance === option}
              onChange={() => setAutoAdvance(option)}
            />
            {t(`rooms.settings.autoAdvance.${option}`)}
          </label>
        ))}
        <TextField
          label={t('rooms.settings.timerSeconds')}
          name="timer_seconds"
          type="number"
          required
          defaultValue={room.settings.timer_seconds}
          disabled={autoAdvance !== 'timer'}
          error={translateFieldError(t, fieldErrors.timer_seconds)}
        />
        <p className="text-muted-foreground">{t('rooms.settings.manualNote')}</p>
      </fieldset>
      <fieldset disabled={isPlaying} className="flex flex-col gap-4">
        <TextField
          label={t('rooms.settings.cooldownSeconds')}
          name="cooldown_seconds"
          type="number"
          required
          defaultValue={room.settings.cooldown_seconds}
          error={translateFieldError(t, fieldErrors.cooldown_seconds)}
        />
        <label className="flex items-center gap-2">
          <input type="checkbox" name="admin_plays" defaultChecked={room.settings.admin_plays} />
          {t('rooms.settings.adminPlays')}
        </label>
      </fieldset>
      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          name="late_arrivals_allowed"
          defaultChecked={room.settings.late_arrivals_allowed}
        />
        {t('rooms.settings.lateArrivals')}
      </label>
      {settingsMutation.isError && (
        <ErrorMessage>{translateError(t, settingsMutation.error)}</ErrorMessage>
      )}
      <DialogActions
        cancelLabel={t('rooms.settings.cancel')}
        onCancel={onCancel}
        submitLabel={
          settingsMutation.isPending ? t('rooms.settings.submitting') : t('rooms.settings.submit')
        }
        submitDisabled={settingsMutation.isPending}
      />
    </form>
  );
}
