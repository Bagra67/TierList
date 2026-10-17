import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { Participant } from '../api/rooms';

interface PlacedListProps {
  // Les participants qui placent les items
  placingParticipants: Participant[];
  placedParticipantIds: string[];
}

type PlacedStatus = 'placed' | 'waiting' | 'disconnected';

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
    <section className="flex w-full flex-col gap-2">
      <h2 className="font-semibold">
        {t('rooms.game.placedCount', {
          placed: connectedPlacedCount,
          count: connected.length,
        })}
      </h2>
      <ul className="flex flex-col gap-1 text-sm">
        {placingParticipants.map((participant) => (
          <li key={participant.id} className="flex gap-2">
            <span className="font-medium">
              {participant.is_you
                ? t('rooms.game.nameYou', { name: participant.display_name })
                : participant.display_name}
            </span>
            <span className="text-muted-foreground">
              {t(`rooms.game.status.${statusOf(participant)}`)}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
