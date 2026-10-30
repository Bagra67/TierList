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
import { type BoardDropTarget, type DropSide, dropPosition, dropSide } from './boardPositions';
import { ErrorMessage } from './ErrorMessage';
import { COOLDOWN_KEYBOARD_CODES, useBoardSensors, useFocusAfterUpdate } from './boardHooks';
import { ITEM_CHIP_CLASS } from './boardStyles';
import {
  type DragPreviewContent,
  DragPreview,
  DraggableItem,
  EndSlot,
  TierLabel,
} from './gameBoardParts';
import { GameItemView } from './GameItemView';
import { MissedItemsPanel } from './MissedItemsPanel';
import { Button } from './ui/button';
import { panelVariants } from './ui/panel';

// Clé de focus d'une tuile : elle garde le focus après un déplacement, même dans une autre rangée
function tileFocusKey(itemId: string): string {
  return `${itemId}:tile`;
}

interface CooldownBoardProps {
  room: Room;
  game: CurrentGame;
  // Sous le panneau des éléments manqués : « Terminer maintenant » pour l'hôte
  aside?: ReactNode;
}

// Le plateau du lecteur pendant les retouches finales (US-4.1, US-4.6) : à gauche ses tiers, où
// toutes les tuiles bougent ; à droite les éléments manqués. Une tuile se glisse à la position
// voulue (souris, doigt, ou Espace puis les flèches au clavier), ou se choisit d'un clic (ou
// Entrée) puis « Déplacer ici » la met à la fin d'un tier.
export function CooldownBoard({ room, game, aside }: CooldownBoardProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const placeMutation = usePlaceItem(room.code);
  const sensors = useBoardSensors(COOLDOWN_KEYBOARD_CODES);
  const sectionRef = useRef<HTMLElement>(null);
  const focus = useFocusAfterUpdate(sectionRef, game.own_placements);
  const pending: boolean = placeMutation.isPending;
  // Tuile choisie pour « Déplacer ici »
  const [chosenId, setChosenId] = useState<string | null>(null);

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

  // Une tuile du plateau ou un élément manqué
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

  async function placeAt(itemId: string, tierId: string, position: number) {
    if (pending) return;
    focus.request([tileFocusKey(itemId)]);
    try {
      await placeMutation.mutateAsync({ tileId: itemId, tierId, position });
    } catch {
      focus.cancel();
      return; // l'erreur est affichée depuis placeMutation.error
    }
  }

  // « Déplacer ici » : la tuile choisie passe à la fin de ce tier (dernière place si elle y est déjà)
  function moveChosenTo(tierId: string) {
    if (chosenId === null) return;
    const tierItemIds: string[] = inTier(tierId).map((placement) => placement.item.id);
    const end: number = tierItemIds.includes(chosenId)
      ? tierItemIds.length - 1
      : tierItemIds.length;
    const itemId: string = chosenId;
    setChosenId(null);
    void placeAt(itemId, tierId, end);
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

  const chosenItem: GameItem | undefined = chosenId === null ? undefined : itemById(chosenId);

  // Aperçu de la tuile glissée, sur le plateau ou parmi les items manqués
  function previewOf(id: string): DragPreviewContent | undefined {
    const item: GameItem | undefined = itemById(id);
    if (item === undefined) return undefined;
    return { item, label: itemLabel(id), className: ITEM_CHIP_CLASS, size: 'small' };
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
    // Déposée sur elle-même, ou là où elle est déjà : elle ne bouge pas
    if (position === null) return;
    setChosenId(null);
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
                chosenId={chosenId}
                chosenLabel={chosenId === null ? '' : itemLabel(chosenId)}
                pending={pending}
                onChoose={toggleChosen}
                onMoveHere={() => moveChosenTo(tier.id)}
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
            focusKeyOf={tileFocusKey}
            chosenId={chosenId}
            pending={pending}
            onChoose={toggleChosen}
          />
          {/* La tuile choisie, annoncée aux lecteurs d'écran quand elle change */}
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
    <li className="flex w-full rounded-[10px] border bg-card">
      {/* Coin arrondi du bloc-lettre : le rayon de la ligne moins sa bordure. Pas d'overflow-hidden
          sur la ligne, qui rognerait l'anneau de focus des tuiles */}
      <TierLabel tier={tier} className="rounded-l-[9px]" />
      <div className="flex flex-1 flex-wrap items-center gap-2 p-2">
        <ol className="flex flex-1 flex-wrap items-center gap-2" aria-label={tier.name}>
          {placements.map((placement) => (
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
          <EndSlot id={`${tier.id}:end`} data={{ tierId: tier.id, itemId: null }} />
        </ol>
        {chosenId !== null && (
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
        )}
      </div>
    </li>
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

// Une tuile du plateau final : elle se glisse ou se choisit, et une autre tuile déposée dessus se
// place avant ou après elle, selon le côté où elle tombe
function CooldownTile({ item, label, tierId, chosen, pending, onChoose }: CooldownTileProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const target: BoardDropTarget = { tierId, itemId: item.id };
  const { setNodeRef, isOver, active }: ReturnType<typeof useDroppable> = useDroppable({
    id: `${tierId}:${item.id}`,
    data: target,
  });
  // La tuile glissée survole sa propre place : rien n'y tomberait
  const highlighted: boolean = isOver && active?.id !== item.id;
  return (
    <li ref={setNodeRef} className={cn('rounded-md', highlighted && 'ring-2 ring-primary')}>
      <DraggableItem
        id={item.id}
        label={label}
        ariaLabel={t('rooms.game.cooldown.chooseLabel', { item: label })}
        focusKey={tileFocusKey(item.id)}
        disabled={pending}
        pressed={chosen}
        onClick={() => onChoose(item.id)}
      >
        <GameItemView item={item} imageLabel={label} size="small" />
      </DraggableItem>
    </li>
  );
}
