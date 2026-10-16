import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { RoomSettings } from '../api/rooms';

interface RoomSettingsSummaryProps {
  settings: RoomSettings;
}

// Réglages de la prochaine partie, lus par tous les participants (le room admin les modifie
// dans RoomSettingsDialog)
export function RoomSettingsSummary({ settings }: RoomSettingsSummaryProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const lines: string[] = [
    t(`rooms.settings.summary.itemOrder.${settings.item_order}`),
    t(`rooms.settings.summary.autoAdvance.${settings.auto_advance}`, {
      seconds: settings.timer_seconds,
    }),
    t('rooms.settings.summary.cooldown', { seconds: settings.cooldown_seconds }),
    settings.admin_plays
      ? t('rooms.settings.summary.adminPlays')
      : t('rooms.settings.summary.adminDoesNotPlay'),
    settings.late_arrivals_allowed
      ? t('rooms.settings.summary.lateArrivalsAllowed')
      : t('rooms.settings.summary.lateArrivalsLocked'),
  ];

  return (
    <ul className="flex list-disc flex-col gap-1 pl-5 text-sm">
      {lines.map((line) => (
        <li key={line}>{line}</li>
      ))}
    </ul>
  );
}
