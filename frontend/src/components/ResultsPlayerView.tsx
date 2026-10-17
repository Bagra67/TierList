import { type ChangeEvent, useId, useState } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { PlayerResults } from '../api/results';
import type { GameItem, GameTier } from '../api/rooms';
import { ResultsTierList } from './ResultsTierList';

interface ResultsPlayerViewProps {
  tiers: GameTier[];
  players: PlayerResults[];
  itemsById: ReadonlyMap<string, GameItem>;
}

// Vue « par joueur » (US-5.2) : le classement final du joueur choisi, avec les items qu'il n'a
// jamais placés
export function ResultsPlayerView({ tiers, players, itemsById }: ResultsPlayerViewProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const selectId: string = useId();
  const [playerIndex, setPlayerIndex] = useState<number>(0);
  const player: PlayerResults | undefined = players[playerIndex];

  if (player === undefined) {
    return <p className="text-muted-foreground">{t('results.players.none')}</p>;
  }

  return (
    <div className="flex w-full flex-col gap-3">
      <div className="flex items-center gap-2">
        <label htmlFor={selectId} className="text-sm font-medium">
          {t('results.players.select')}
        </label>
        <select
          id={selectId}
          value={playerIndex}
          onChange={(event: ChangeEvent<HTMLSelectElement>) =>
            setPlayerIndex(Number(event.target.value))
          }
          className="h-8 rounded-lg border border-input bg-transparent px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          {/* La réponse ne donne pas d'identifiant aux joueurs : leur rang, fixe, sert de valeur */}
          {players.map((candidate: PlayerResults, index: number) => (
            <option key={index} value={index}>
              {candidate.display_name}
            </option>
          ))}
        </select>
      </div>
      <ResultsTierList
        tiers={tiers}
        rows={player.tiers}
        itemsById={itemsById}
        extraRow={{ label: t('results.players.unplaced'), itemIds: player.unplaced_item_ids }}
      />
    </div>
  );
}
