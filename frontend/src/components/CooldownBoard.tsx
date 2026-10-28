import {
  closestCenter,
  DndContext,
  useDroppable,
  type Announcements,
  type DragEndEvent,
  type UniqueIdentifier,
} from '@dnd-kit/core';
import { cn } from 'cn';
import { type ChangeEvent, useId, useRef, useState } from 'react';
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
import { type BoardDropTarget, type DropSide, dropPosition, dropSide } from './boardPositions';
import { ErrorMessage } from './ErrorMessage';
import { useBoardSensors, useFocusAfterUpdate } from './boardHooks';
import { DraggableItem, EndSlot, TierLabel } from './gameBoardParts';
import { GameItemView } from './GameItemView';
import { Button } from './ui/button';

// Les contrôles d'une tuile, pour lui rendre le focus après un déplacement
type TileControl = 'drag' | 'earlier' | 'later' | 'up' | 'down';

function focusKey(itemId: string, control: TileControl): string {
  return `${itemId}:${control}`;
}

// Place une tuile à ce rang de ce tier, puis rend le focus au premier de ces contrôles
type PlaceHandler = (
  itemId: string,
  tierId: string,
  position: number,
  focusControls: TileControl[],
) => void;

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
  const sensors = useBoardSensors();
  const sectionRef = useRef<HTMLElement>(null);
  const focus = useFocusAfterUpdate(sectionRef, game.own_placements);
  const pending: boolean = placeMutation.isPending;

  // Les tuiles d'un tier, dans l'ordre (le serveur les trie)
  function inTier(tierId: string): OwnPlacement[] {
    return game.own_placements.filter((placement) => placement.tier_id === tierId);
  }

  function tierName(tierId: string): string {
    return game.tiers.find((tier) => tier.id === tierId)?.name ?? '';
  }

  // Nom de chaque tuile, lu par les lecteurs d'écran ; une image seule est nommée par sa place,
  // pour que ses boutons ne portent pas tous le même nom
  const labels: Map<string, string> = new Map();
  for (const tier of game.tiers) {
    inTier(tier.id).forEach((placement, index) => {
      labels.set(
        placement.item.id,
        placement.item.text ??
          t('rooms.game.imageItemAt', { tier: tier.name, position: index + 1 }),
      );
    });
  }
  game.missed_items.forEach((item, index) => {
    labels.set(item.id, item.text ?? t('rooms.game.cooldown.missedImage', { position: index + 1 }));
  });

  function itemLabel(itemId: UniqueIdentifier): string {
    return labels.get(String(itemId)) ?? '';
  }

  function positionFor(itemId: string, target: BoardDropTarget, side: DropSide): number | null {
    const tierItemIds: string[] = inTier(target.tierId).map((placement) => placement.item.id);
    return dropPosition(tierItemIds, itemId, target, side);
  }

  async function placeAt(
    itemId: string,
    tierId: string,
    position: number,
    focusControls: TileControl[],
  ) {
    if (pending) return;
    // La tuile garde le focus, même déplacée dans une autre rangée ; un item manqué placé le
    // retrouve sur le plateau
    const controls: TileControl[] = [...focusControls, 'drag'];
    focus.request(controls.map((control) => focusKey(itemId, control)));
    try {
      await placeMutation.mutateAsync({ tileId: itemId, tierId, position });
    } catch {
      focus.cancel();
      return; // l'erreur est affichée depuis placeMutation.error
    }
  }

  function announce(
    key: 'rooms.game.dnd.over' | 'rooms.game.dnd.dropped',
    itemId: UniqueIdentifier,
    target: BoardDropTarget,
    side: DropSide,
  ): string {
    const position: number | null = positionFor(String(itemId), target, side);
    if (position === null) return t('rooms.game.dnd.unchanged', { item: itemLabel(itemId) });
    return t(key, {
      item: itemLabel(itemId),
      tier: tierName(target.tierId),
      position: position + 1,
    });
  }

  const announcements: Announcements = {
    onDragStart: ({ active }) => t('rooms.game.dnd.pickedUp', { item: itemLabel(active.id) }),
    onDragOver: ({ active, over }) =>
      over?.data.current === undefined
        ? undefined
        : announce(
            'rooms.game.dnd.over',
            active.id,
            over.data.current as BoardDropTarget,
            dropSide(active.rect.current.translated, over.rect),
          ),
    onDragEnd: ({ active, over }) =>
      over?.data.current === undefined
        ? undefined
        : announce(
            'rooms.game.dnd.dropped',
            active.id,
            over.data.current as BoardDropTarget,
            dropSide(active.rect.current.translated, over.rect),
          ),
    onDragCancel: ({ active }) => t('rooms.game.dnd.cancelled', { item: itemLabel(active.id) }),
  };

  function handleDragEnd({ active, over }: DragEndEvent) {
    if (over?.data.current === undefined) return;
    const target: BoardDropTarget = over.data.current as BoardDropTarget;
    const itemId: string = String(active.id);
    const position: number | null = positionFor(
      itemId,
      target,
      dropSide(active.rect.current.translated, over.rect),
    );
    // Déposée sur elle-même, ou là où elle est déjà : elle ne bouge pas
    if (position === null) return;
    void placeAt(itemId, target.tierId, position, ['drag']);
  }

  const onPlace: PlaceHandler = (itemId, tierId, position, focusControls) =>
    void placeAt(itemId, tierId, position, focusControls);

  return (
    <section ref={sectionRef} className="flex w-full flex-col gap-3">
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
            labelOf={itemLabel}
            endOf={(tierId) => inTier(tierId).length}
            pending={pending}
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
                labelOf={itemLabel}
                above={
                  above === undefined ? undefined : { tier: above, end: inTier(above.id).length }
                }
                below={
                  below === undefined ? undefined : { tier: below, end: inTier(below.id).length }
                }
                pending={pending}
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
  labelOf: (itemId: string) => string;
  above: NeighbourTier | undefined;
  below: NeighbourTier | undefined;
  pending: boolean;
  onPlace: PlaceHandler;
}

function CooldownTierRow({
  tier,
  placements,
  labelOf,
  above,
  below,
  pending,
  onPlace,
}: CooldownTierRowProps) {
  return (
    <li className="flex w-full rounded-[10px] border bg-card">
      {/* Coin arrondi du bloc-lettre : le rayon de la ligne moins sa bordure. Pas d'overflow-hidden
          sur la ligne, qui rognerait l'item glissé vers un autre tier */}
      <TierLabel tier={tier} className="rounded-l-[9px]" />
      <div className="flex flex-1 flex-wrap items-center gap-2 p-2">
        <ol className="flex flex-1 flex-wrap items-center gap-2" aria-label={tier.name}>
          {placements.map((placement, index) => (
            <CooldownTile
              key={placement.item.id}
              item={placement.item}
              label={labelOf(placement.item.id)}
              tierId={tier.id}
              index={index}
              count={placements.length}
              above={above}
              below={below}
              pending={pending}
              onPlace={onPlace}
            />
          ))}
          <EndSlot id={`${tier.id}:end`} data={{ tierId: tier.id, itemId: null }} />
        </ol>
      </div>
    </li>
  );
}

interface CooldownTileProps {
  item: GameItem;
  label: string;
  tierId: string;
  // Rang de la tuile dans son tier, et nombre de tuiles du tier
  index: number;
  count: number;
  above: NeighbourTier | undefined;
  below: NeighbourTier | undefined;
  pending: boolean;
  onPlace: PlaceHandler;
}

// Une tuile du plateau final : elle se glisse, et une autre tuile déposée dessus se place avant
// ou après elle, selon le côté où elle tombe
function CooldownTile({
  item,
  label,
  tierId,
  index,
  count,
  above,
  below,
  pending,
  onPlace,
}: CooldownTileProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const target: BoardDropTarget = { tierId, itemId: item.id };
  const { setNodeRef, isOver, active }: ReturnType<typeof useDroppable> = useDroppable({
    id: `${tierId}:${item.id}`,
    data: target,
  });
  // La tuile glissée survole sa propre place : rien n'y tomberait
  const highlighted: boolean = isOver && active?.id !== item.id;
  return (
    <li
      ref={setNodeRef}
      className={cn('flex items-center gap-1 rounded-md', highlighted && 'ring-2 ring-primary')}
    >
      <DraggableItem
        id={item.id}
        label={label}
        focusKey={focusKey(item.id, 'drag')}
        disabled={pending}
      >
        <GameItemView item={item} imageLabel={label} size="small" />
      </DraggableItem>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        data-focus-key={focusKey(item.id, 'earlier')}
        aria-label={t('rooms.game.moveEarlier', { item: label })}
        aria-disabled={pending}
        disabled={index === 0}
        onClick={() => onPlace(item.id, tierId, index - 1, ['earlier', 'later'])}
      >
        ←
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        data-focus-key={focusKey(item.id, 'later')}
        aria-label={t('rooms.game.moveLater', { item: label })}
        aria-disabled={pending}
        disabled={index >= count - 1}
        onClick={() => onPlace(item.id, tierId, index + 1, ['later', 'earlier'])}
      >
        →
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        data-focus-key={focusKey(item.id, 'up')}
        aria-label={t('rooms.game.cooldown.moveUp', { item: label })}
        aria-disabled={pending}
        disabled={above === undefined}
        onClick={() =>
          above !== undefined && onPlace(item.id, above.tier.id, above.end, ['up', 'down'])
        }
      >
        ↑
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        data-focus-key={focusKey(item.id, 'down')}
        aria-label={t('rooms.game.cooldown.moveDown', { item: label })}
        aria-disabled={pending}
        disabled={below === undefined}
        onClick={() =>
          below !== undefined && onPlace(item.id, below.tier.id, below.end, ['down', 'up'])
        }
      >
        ↓
      </Button>
    </li>
  );
}

interface MissedItemsProps {
  items: GameItem[];
  tiers: GameTier[];
  labelOf: (itemId: string) => string;
  // Rang de la fin d'un tier : un item manqué s'y place en dernier
  endOf: (tierId: string) => number;
  pending: boolean;
  onPlace: PlaceHandler;
}

// Les items manqués (votes absents, arrivée en retard), à placer avant la fin du cooldown (US-4.6)
function MissedItems({ items, tiers, labelOf, endOf, pending, onPlace }: MissedItemsProps) {
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
            label={labelOf(item.id)}
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
  label: string;
  tiers: GameTier[];
  endOf: (tierId: string) => number;
  pending: boolean;
  onPlace: PlaceHandler;
}

function MissedItemRow({ item, label, tiers, endOf, pending, onPlace }: MissedItemRowProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const selectId: string = useId();
  // Les tiers sont figés pour toute la partie : le premier reste le même
  const [tierId, setTierId] = useState<string>(tiers[0]?.id ?? '');
  return (
    <li className="flex flex-wrap items-center gap-2">
      <DraggableItem
        id={item.id}
        label={label}
        focusKey={focusKey(item.id, 'drag')}
        disabled={pending}
      >
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
        className="h-8 rounded-lg border border-input bg-transparent px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring"
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
        aria-disabled={pending}
        onClick={() => onPlace(item.id, tierId, endOf(tierId), [])}
      >
        {t('rooms.game.cooldown.place')}
      </Button>
    </li>
  );
}
