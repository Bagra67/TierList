import {
  closestCenter,
  DndContext,
  KeyboardSensor,
  PointerSensor,
  useDroppable,
  useSensor,
  useSensors,
  type Announcements,
  type DragEndEvent,
  type SensorDescriptor,
  type SensorOptions,
  type UniqueIdentifier,
} from '@dnd-kit/core';
import { cn } from 'cn';
import { type ChangeEvent, useId, useState } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import {
  type CurrentGame,
  type GameItem,
  type GameTier,
  type OwnPlacement,
  type Room,
  usePlaceItem,
} from '../api/rooms';
import { translateError } from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { DraggableItem, EndSlot, TierLabel } from './gameBoardParts';
import { GameItemView } from './GameItemView';
import { Button } from './ui/button';

// Où une tuile serait posée : un tier, et la tuile devant laquelle elle irait (null : à la fin)
type CooldownDropTarget = {
  tierId: string;
  beforeItemId: string | null;
};

// Place une tuile à ce rang de ce tier
type PlaceHandler = (itemId: string, tierId: string, position: number) => void;

interface CooldownBoardProps {
  room: Room;
  game: CurrentGame;
}

// Le plateau du lecteur pendant le cooldown final (US-4.1, US-4.6) : toutes ses tuiles bougent, et
// les items qu'il a manqués attendent à part. À la souris ou au doigt par glisser-déposer ; au
// clavier par les boutons ←/→ (dans le tier), ↑/↓ (tier voisin) et la liste « Placer dans ».
export function CooldownBoard({ room, game }: CooldownBoardProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const placeMutation = usePlaceItem(room.code);
  const sensors: SensorDescriptor<SensorOptions>[] = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor),
  );
  const items: GameItem[] = [
    ...game.own_placements.map((placement) => placement.item),
    ...game.missed_items,
  ];

  // Les tuiles d'un tier, dans l'ordre (le serveur les trie)
  function inTier(tierId: string): OwnPlacement[] {
    return game.own_placements.filter((placement) => placement.tier_id === tierId);
  }

  function itemLabel(itemId: UniqueIdentifier): string {
    const item: GameItem | undefined = items.find((candidate) => candidate.id === itemId);
    return item?.text ?? t('rooms.game.placedItemImage');
  }

  function tierName(tierId: string): string {
    return game.tiers.find((tier) => tier.id === tierId)?.name ?? '';
  }

  // Rang parmi les autres tuiles du tier visé, sans celle qui bouge : la position du serveur
  function positionOf(itemId: string, target: CooldownDropTarget): number {
    const others: OwnPlacement[] = inTier(target.tierId).filter(
      (placement) => placement.item.id !== itemId,
    );
    const index: number = others.findIndex(
      (placement) => placement.item.id === target.beforeItemId,
    );
    return index === -1 ? others.length : index;
  }

  async function placeAt(itemId: string, tierId: string, position: number) {
    try {
      await placeMutation.mutateAsync({ tileId: itemId, tierId, position });
    } catch {
      return; // l'erreur est affichée depuis placeMutation.error
    }
  }

  function describe(itemId: UniqueIdentifier, target: CooldownDropTarget) {
    return {
      item: itemLabel(itemId),
      tier: tierName(target.tierId),
      position: positionOf(String(itemId), target) + 1,
    };
  }

  const announcements: Announcements = {
    onDragStart: ({ active }) => t('rooms.game.dnd.pickedUp', { item: itemLabel(active.id) }),
    onDragOver: ({ active, over }) =>
      over?.data.current === undefined
        ? undefined
        : t('rooms.game.dnd.over', describe(active.id, over.data.current as CooldownDropTarget)),
    onDragEnd: ({ active, over }) =>
      over?.data.current === undefined
        ? undefined
        : t('rooms.game.dnd.dropped', describe(active.id, over.data.current as CooldownDropTarget)),
    onDragCancel: ({ active }) => t('rooms.game.dnd.cancelled', { item: itemLabel(active.id) }),
  };

  function handleDragEnd({ active, over }: DragEndEvent) {
    if (over?.data.current === undefined) return;
    const target: CooldownDropTarget = over.data.current as CooldownDropTarget;
    const itemId: string = String(active.id);
    // Déposée sur elle-même : elle ne bouge pas
    if (target.beforeItemId === itemId) return;
    void placeAt(itemId, target.tierId, positionOf(itemId, target));
  }

  const onPlace: PlaceHandler = (itemId, tierId, position) =>
    void placeAt(itemId, tierId, position);

  return (
    <section className="flex w-full flex-col gap-3">
      <h2 className="text-lg font-semibold">{t('rooms.game.board')}</h2>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
        accessibility={{
          announcements,
          screenReaderInstructions: { draggable: t('rooms.game.dnd.instructions') },
        }}
      >
        {game.missed_items.length > 0 && (
          <MissedItems
            items={game.missed_items}
            tiers={game.tiers}
            endOf={(tierId) => inTier(tierId).length}
            pending={placeMutation.isPending}
            onPlace={onPlace}
          />
        )}
        <ol className="flex w-full flex-col gap-2">
          {game.tiers.map((tier, index) => {
            const above: GameTier | undefined = game.tiers[index - 1];
            const below: GameTier | undefined = game.tiers[index + 1];
            return (
              <CooldownTierRow
                key={tier.id}
                tier={tier}
                placements={inTier(tier.id)}
                above={
                  above === undefined ? undefined : { tier: above, end: inTier(above.id).length }
                }
                below={
                  below === undefined ? undefined : { tier: below, end: inTier(below.id).length }
                }
                pending={placeMutation.isPending}
                onPlace={onPlace}
              />
            );
          })}
        </ol>
      </DndContext>
      {placeMutation.isError && (
        <ErrorMessage>{translateError(t, placeMutation.error)}</ErrorMessage>
      )}
    </section>
  );
}

// Un tier voisin, et le rang de sa fin : ↑/↓ y mettent la tuile en dernier
interface NeighbourTier {
  tier: GameTier;
  end: number;
}

interface CooldownTierRowProps {
  tier: GameTier;
  placements: OwnPlacement[];
  above: NeighbourTier | undefined;
  below: NeighbourTier | undefined;
  pending: boolean;
  onPlace: PlaceHandler;
}

function CooldownTierRow({
  tier,
  placements,
  above,
  below,
  pending,
  onPlace,
}: CooldownTierRowProps) {
  return (
    <li className="flex w-full flex-wrap items-center gap-2 rounded-lg border p-2">
      <TierLabel tier={tier} />
      <ol className="flex flex-1 flex-wrap items-center gap-2" aria-label={tier.name}>
        {placements.map((placement, index) => (
          <CooldownTile
            key={placement.item.id}
            item={placement.item}
            tierId={tier.id}
            index={index}
            count={placements.length}
            above={above}
            below={below}
            pending={pending}
            onPlace={onPlace}
          />
        ))}
        <EndSlot id={`${tier.id}:end`} data={{ tierId: tier.id, beforeItemId: null }} />
      </ol>
    </li>
  );
}

interface CooldownTileProps {
  item: GameItem;
  tierId: string;
  // Rang de la tuile dans son tier, et nombre de tuiles du tier
  index: number;
  count: number;
  above: NeighbourTier | undefined;
  below: NeighbourTier | undefined;
  pending: boolean;
  onPlace: PlaceHandler;
}

// Une tuile du plateau final : elle se glisse, et déposer une autre tuile dessus la place avant elle
function CooldownTile({
  item,
  tierId,
  index,
  count,
  above,
  below,
  pending,
  onPlace,
}: CooldownTileProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const label: string = item.text ?? t('rooms.game.placedItemImage');
  const target: CooldownDropTarget = { tierId, beforeItemId: item.id };
  const { setNodeRef, isOver }: ReturnType<typeof useDroppable> = useDroppable({
    id: `${tierId}:${item.id}`,
    data: target,
  });
  return (
    <li
      ref={setNodeRef}
      className={cn(
        'flex items-center gap-1',
        // L'endroit où la tuile tomberait : juste avant celle-ci
        isOver && 'border-l-4 border-dashed border-primary pl-1',
      )}
    >
      <DraggableItem id={item.id} label={label} disabled={pending}>
        <GameItemView item={item} imageLabel={label} size="small" />
      </DraggableItem>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        aria-label={t('rooms.game.moveEarlier', { item: label })}
        disabled={pending || index === 0}
        onClick={() => onPlace(item.id, tierId, index - 1)}
      >
        ←
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        aria-label={t('rooms.game.moveLater', { item: label })}
        disabled={pending || index >= count - 1}
        onClick={() => onPlace(item.id, tierId, index + 1)}
      >
        →
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        aria-label={t('rooms.game.cooldown.moveUp', { item: label })}
        disabled={pending || above === undefined}
        onClick={() => above !== undefined && onPlace(item.id, above.tier.id, above.end)}
      >
        ↑
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        aria-label={t('rooms.game.cooldown.moveDown', { item: label })}
        disabled={pending || below === undefined}
        onClick={() => below !== undefined && onPlace(item.id, below.tier.id, below.end)}
      >
        ↓
      </Button>
    </li>
  );
}

interface MissedItemsProps {
  items: GameItem[];
  tiers: GameTier[];
  // Rang de la fin d'un tier : un item manqué s'y place en dernier
  endOf: (tierId: string) => number;
  pending: boolean;
  onPlace: PlaceHandler;
}

// Les items manqués (votes absents, arrivée en retard), à placer avant la fin du cooldown (US-4.6)
function MissedItems({ items, tiers, endOf, pending, onPlace }: MissedItemsProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const headingId: string = useId();
  return (
    <section
      aria-labelledby={headingId}
      className="flex flex-col gap-2 rounded-lg border border-dashed p-3"
    >
      <h3 id={headingId} className="font-semibold">
        {t('rooms.game.cooldown.missed')}
      </h3>
      <ul className="flex flex-col gap-2">
        {items.map((item) => (
          <MissedItemRow
            key={item.id}
            item={item}
            tiers={tiers}
            endOf={endOf}
            pending={pending}
            onPlace={onPlace}
          />
        ))}
      </ul>
    </section>
  );
}

interface MissedItemRowProps {
  item: GameItem;
  tiers: GameTier[];
  endOf: (tierId: string) => number;
  pending: boolean;
  onPlace: PlaceHandler;
}

function MissedItemRow({ item, tiers, endOf, pending, onPlace }: MissedItemRowProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const selectId: string = useId();
  const [tierId, setTierId] = useState<string>(tiers[0]?.id ?? '');
  const label: string = item.text ?? t('rooms.game.placedItemImage');
  return (
    <li className="flex flex-wrap items-center gap-2">
      <DraggableItem id={item.id} label={label} disabled={pending}>
        <GameItemView item={item} imageLabel={label} size="small" />
      </DraggableItem>
      {/* Le mot accompagne la couleur, qui ne suffirait pas seule */}
      <span className="rounded-sm bg-destructive/10 px-1 text-xs font-semibold uppercase text-destructive">
        {t('rooms.game.cooldown.absent')}
      </span>
      <label htmlFor={selectId} className="sr-only">
        {t('rooms.game.cooldown.placeInLabel', { item: label })}
      </label>
      <select
        id={selectId}
        value={tierId}
        onChange={(event: ChangeEvent<HTMLSelectElement>) => setTierId(event.target.value)}
        className="h-8 rounded-lg border border-input bg-transparent px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
      >
        {tiers.map((tier) => (
          <option key={tier.id} value={tier.id}>
            {tier.name}
          </option>
        ))}
      </select>
      <Button
        type="button"
        variant="outline"
        size="sm"
        aria-label={t('rooms.game.cooldown.placeLabel', { item: label })}
        disabled={pending}
        onClick={() => onPlace(item.id, tierId, endOf(tierId))}
      >
        {t('rooms.game.cooldown.place')}
      </Button>
    </li>
  );
}
