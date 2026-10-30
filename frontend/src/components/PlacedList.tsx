import { Check, Circle, CircleDashed, type LucideIcon } from 'lucide-react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { Participant } from '../api/rooms';
import { panelVariants } from './ui/panel';

interface PlacedListProps {
  // Les participants qui placent les items
  placingParticipants: Participant[];
  placedParticipantIds: string[];
}

type PlacedStatus = 'placed' | 'waiting' | 'disconnected';

// Pastille de chaque état ; le mot l'accompagne toujours, la forme ne suffit pas seule
const STATUS_ICONS: Record<PlacedStatus, LucideIcon> = {
  placed: Check,
  waiting: Circle,
  disconnected: CircleDashed,
};

// Qui a placé l'item en cours, jamais où (plateau privé, US-3.3). Le compteur n'attend que les
// participants connectés (US-3.4)
export function PlacedList({ placingParticipants, placedParticipantIds }: PlacedListProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const placed: Set<string> = new Set(placedParticipantIds);
  const connected: Participant[] = placingParticipants.filter(
    (participant) => participant.connected,
  );
  const connectedPlacedCount: number = connected.filter((participant) =>
    placed.has(participant.id),
  ).length;

  function statusOf(participant: Participant): PlacedStatus {
    if (placed.has(participant.id)) return 'placed';
    return participant.connected ? 'waiting' : 'disconnected';
  }

  return (
    <section className={panelVariants()}>
      <h2 className="font-heading text-xl font-black">
        {t('rooms.game.placedCount', {
          placed: connectedPlacedCount,
          count: connected.length,
        })}
      </h2>
      <ul className="flex flex-col gap-1.5 text-sm">
        {placingParticipants.map((participant) => {
          const status: PlacedStatus = statusOf(participant);
          const StatusIcon: LucideIcon = STATUS_ICONS[status];
          return (
            <li key={participant.id} className="flex items-center gap-2">
              <StatusIcon
                className={
                  status === 'placed' ? 'size-4 text-success' : 'size-4 text-muted-foreground'
                }
              />
              <span className="font-medium">
                {participant.is_you
                  ? t('rooms.game.nameYou', { name: participant.display_name })
                  : participant.display_name}
              </span>
              <span className="ml-auto text-muted-foreground">
                {t(`rooms.game.status.${status}`)}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
