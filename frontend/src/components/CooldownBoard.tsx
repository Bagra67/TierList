import {
  closestCenter,
  DndContext,
  useDroppable,
  type Announcements,
  type DragEndEvent,
  type UniqueIdentifier,
} from '@dnd-kit/core';
import { cn } from 'cn';
import { type ReactNode, useRef, useState } from 'react';
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
import {
  type BoardDropTarget,
  type DropSide,
  dropPosition,
  dropSide,
  tierNameIn,
} from './boardPositions';
import { ErrorMessage } from './ErrorMessage';
import {
  ENTER_CHOOSES_TILE_KEYBOARD_CODES,
  tileFocusKey,
  useBoardSensors,
  useFocusAfterUpdate,
} from './boardHooks';
import { ITEM_CHIP_CLASS } from './boardStyles';
import {
  BoardTierRow,
  ChoosableTile,
  DragPreview,
  type DragPreviewContent,
} from './gameBoardParts';
import { MissedItemsPanel } from './MissedItemsPanel';
import { Button } from './ui/button';
import { panelVariants } from './ui/panel';

interface CooldownBoardProps {
  room: Room;
  game: CurrentGame;
  aside?: ReactNode;
}

export function CooldownBoard({ room, game, aside }: CooldownBoardProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const placeMutation = usePlaceItem(room.code);
  const sensors = useBoardSensors(ENTER_CHOOSES_TILE_KEYBOARD_CODES);
  const sectionRef = useRef<HTMLElement>(null);
  const focus = useFocusAfterUpdate(sectionRef, game.own_placements);
  const pending: boolean = placeMutation.isPending;
  const [chosenId, setChosenId] = useState<string | null>(null);
  const [buttonPlacementAnnouncement, setButtonPlacementAnnouncement] = useState<string>('');

  function inTier(tierId: string): OwnPlacement[] {
    return game.own_placements.filter((placement) => placement.tier_id === tierId);
  }

  function tierName(tierId: string): string {
    return tierNameIn(game, tierId);
  }

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

  function itemById(itemId: string): GameItem | undefined {
    return (
      game.own_placements.find((placement) => placement.item.id === itemId)?.item ??
      game.missed_items.find((item) => item.id === itemId)
    );
  }

  function positionFor(itemId: string, target: BoardDropTarget, side: DropSide): number | null {
    const tierItemIds: string[] = inTier(target.tierId).map((placement) => placement.item.id);
    return dropPosition(tierItemIds, itemId, target, side);
  }

  async function placeAt(itemId: string, tierId: string, position: number): Promise<boolean> {
    if (pending) return false;
    focus.focusFirstEnabledAfterUpdate([tileFocusKey(itemId)]);
    try {
      await placeMutation.mutateAsync({ tileId: itemId, tierId, position });
      return true;
    } catch {
      focus.cancel();
      return false;
    }
  }

  const chosenItem: GameItem | undefined = chosenId === null ? undefined : itemById(chosenId);

  async function moveChosenTo(tierId: string) {
    if (chosenItem === undefined || pending) return;
    const itemId: string = chosenItem.id;
    const tierItemIds: string[] = inTier(tierId).map((placement) => placement.item.id);
    const currentIndex: number = tierItemIds.indexOf(itemId);
    if (currentIndex !== -1 && currentIndex === tierItemIds.length - 1) {
      setChosenId(null);
      return;
    }
    const end: number = currentIndex === -1 ? tierItemIds.length : tierItemIds.length - 1;
    if (await placeAt(itemId, tierId, end)) {
      setChosenId(null);
      setButtonPlacementAnnouncement(
        t('rooms.game.dnd.dropped', {
          item: itemLabel(itemId),
          tier: tierName(tierId),
          position: end + 1,
        }),
      );
    }
  }

  function toggleChosen(itemId: string) {
    setChosenId((current) => (current === itemId ? null : itemId));
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

  function previewOf(id: string): DragPreviewContent | undefined {
    const item: GameItem | undefined = itemById(id);
    if (item === undefined) return undefined;
    return { item, label: itemLabel(id), sourceShapeClassName: ITEM_CHIP_CLASS, size: 'small' };
  }

  function handleDragEnd({ active, over }: DragEndEvent) {
    if (over?.data.current === undefined) return;
    const target: BoardDropTarget = over.data.current as BoardDropTarget;
    const itemId: string = String(active.id);
    const position: number | null = positionFor(
      itemId,
      target,
      dropSide(active.rect.current.translated, over.rect),
    );
    if (position === null) return;
    if (itemId === chosenId) setChosenId(null);
    void placeAt(itemId, target.tierId, position);
  }

  return (
    <section
      ref={sectionRef}
      className="grid w-full items-start gap-x-6 gap-y-3 lg:grid-cols-[minmax(0,1fr)_18rem]"
    >
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
        accessibility={{
          announcements,
          screenReaderInstructions: { draggable: t('rooms.game.cooldown.dndInstructions') },
        }}
      >
        <div className="flex min-w-0 flex-col gap-3">
          <h2 className="text-lg font-semibold">{t('rooms.game.board')}</h2>
          <ol className="flex w-full flex-col gap-2">
            {game.tiers.map((tier) => (
              <CooldownTierRow
                key={tier.id}
                tier={tier}
                placements={inTier(tier.id)}
                labelOf={itemLabel}
                chosenId={chosenItem?.id ?? null}
                chosenLabel={chosenItem === undefined ? '' : itemLabel(chosenItem.id)}
                pending={pending}
                onChoose={toggleChosen}
                onMoveHere={() => void moveChosenTo(tier.id)}
              />
            ))}
          </ol>
          {placeMutation.isError && (
            <ErrorMessage>{translateError(t, placeMutation.error)}</ErrorMessage>
          )}
        </div>
        <aside className="flex flex-col gap-4">
          <MissedItemsPanel
            items={game.missed_items}
            labelOf={itemLabel}
            chosenId={chosenItem?.id ?? null}
            pending={pending}
            onChoose={toggleChosen}
          />
          <div aria-live="polite" className={panelVariants({ variant: 'muted' })}>
            {chosenItem === undefined ? (
              <p className="text-sm text-muted-foreground">{t('rooms.game.cooldown.chooseHint')}</p>
            ) : (
              <>
                <p className="text-sm">
                  {t('rooms.game.cooldown.chosen', { item: itemLabel(chosenItem.id) })}
                </p>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="self-start"
                  onClick={() => setChosenId(null)}
                >
                  {t('rooms.game.cooldown.cancelChoice')}
                </Button>
              </>
            )}
          </div>
          {aside}
        </aside>
        <DragPreview previewOf={previewOf} />
      </DndContext>
      <p role="status" className="sr-only">
        {buttonPlacementAnnouncement}
      </p>
    </section>
  );
}

interface CooldownTierRowProps {
  tier: GameTier;
  placements: OwnPlacement[];
  labelOf: (itemId: string) => string;
  chosenId: string | null;
  chosenLabel: string;
  pending: boolean;
  onChoose: (itemId: string) => void;
  onMoveHere: () => void;
}

function CooldownTierRow({
  tier,
  placements,
  labelOf,
  chosenId,
  chosenLabel,
  pending,
  onChoose,
  onMoveHere,
}: CooldownTierRowProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  return (
    <BoardTierRow
      tier={tier}
      items={placements.map((placement) => (
        <CooldownTile
          key={placement.item.id}
          item={placement.item}
          label={labelOf(placement.item.id)}
          tierId={tier.id}
          chosen={chosenId === placement.item.id}
          pending={pending}
          onChoose={onChoose}
        />
      ))}
      action={
        chosenId !== null && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            aria-label={t('rooms.game.cooldown.moveHereLabel', {
              item: chosenLabel,
              tier: tier.name,
            })}
            aria-disabled={pending}
            onClick={onMoveHere}
          >
            {t('rooms.game.cooldown.moveHere')}
          </Button>
        )
      }
    />
  );
}

interface CooldownTileProps {
  item: GameItem;
  label: string;
  tierId: string;
  chosen: boolean;
  pending: boolean;
  onChoose: (itemId: string) => void;
}

function CooldownTile({ item, label, tierId, chosen, pending, onChoose }: CooldownTileProps) {
  const target: BoardDropTarget = { tierId, itemId: item.id };
  const { setNodeRef, isOver, active }: ReturnType<typeof useDroppable> = useDroppable({
    id: `${tierId}:${item.id}`,
    data: target,
  });
  const hoveredByAnotherTile: boolean = isOver && active?.id !== item.id;
  return (
    <li
      ref={setNodeRef}
      className={cn('rounded-md', hoveredByAnotherTile && 'ring-2 ring-primary')}
    >
      <ChoosableTile
        item={item}
        label={label}
        chosen={chosen}
        pending={pending}
        onChoose={onChoose}
      />
    </li>
  );
}
