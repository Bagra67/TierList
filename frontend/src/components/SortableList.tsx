import {
  closestCenter,
  DndContext,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type Announcements,
  type DragEndEvent,
  type SensorDescriptor,
  type SensorOptions,
  type UniqueIdentifier,
} from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  type SortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
  type ButtonHTMLAttributes,
  type CSSProperties,
  type ReactNode,
  type RefObject,
  useRef,
} from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

interface SortableItem {
  id: string;
}

type DragHandleProps = ButtonHTMLAttributes<HTMLButtonElement>;

interface SortableListProps<Item extends SortableItem> {
  items: Item[];
  strategy: SortingStrategy;
  getItemLabel: (item: Item) => string;
  onMove: (item: Item, newIndex: number) => void;
  disabled?: boolean;
  renderItem: (item: Item, sortable: SortableRender) => ReactNode;
}

interface SortableRender {
  setNodeRef: (element: HTMLElement | null) => void;
  style: CSSProperties;
  handleProps: DragHandleProps;
}

export function SortableList<Item extends SortableItem>({
  items,
  strategy,
  getItemLabel,
  onMove,
  disabled = false,
  renderItem,
}: SortableListProps<Item>) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const hasLeftItsPlace: RefObject<boolean> = useRef<boolean>(false);
  const sensors: SensorDescriptor<SensorOptions>[] = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  function findItem(id: UniqueIdentifier): Item | undefined {
    return items.find((item) => item.id === id);
  }

  function positionOf(id: UniqueIdentifier): number {
    return items.findIndex((item) => item.id === id) + 1;
  }

  function describe(id: UniqueIdentifier, positionId: UniqueIdentifier = id) {
    const item: Item | undefined = findItem(id);
    return {
      item: item === undefined ? '' : getItemLabel(item),
      position: positionOf(positionId),
      count: items.length,
    };
  }

  const announcements: Announcements = {
    onDragStart: ({ active }) => {
      hasLeftItsPlace.current = false;
      return t('templates.editor.dnd.pickedUp', describe(active.id));
    },
    onDragOver: ({ active, over }) => {
      if (over === null) return undefined;
      if (over.id === active.id && !hasLeftItsPlace.current) return undefined;
      hasLeftItsPlace.current = true;
      return t('templates.editor.dnd.movedOver', describe(active.id, over.id));
    },
    onDragEnd: ({ active, over }) =>
      over ? t('templates.editor.dnd.dropped', describe(active.id, over.id)) : undefined,
    onDragCancel: ({ active }) => t('templates.editor.dnd.cancelled', describe(active.id)),
  };

  function handleDragEnd({ active, over }: DragEndEvent) {
    if (over === null || active.id === over.id) return;
    const movedItem: Item | undefined = findItem(active.id);
    const newIndex: number = items.findIndex((item) => item.id === over.id);
    if (movedItem !== undefined && newIndex !== -1) {
      onMove(movedItem, newIndex);
    }
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={handleDragEnd}
      accessibility={{
        announcements,
        screenReaderInstructions: { draggable: t('templates.editor.dnd.instructions') },
      }}
    >
      <SortableContext items={items} strategy={strategy} disabled={disabled}>
        {items.map((item) => (
          <SortableEntry key={item.id} item={item} renderItem={renderItem} />
        ))}
      </SortableContext>
    </DndContext>
  );
}

interface SortableEntryProps<Item extends SortableItem> {
  item: Item;
  renderItem: (item: Item, sortable: SortableRender) => ReactNode;
}

function SortableEntry<Item extends SortableItem>({ item, renderItem }: SortableEntryProps<Item>) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  }: ReturnType<typeof useSortable> = useSortable({
    id: item.id,
  });
  const style: CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 1 : undefined,
    position: 'relative',
  };
  const handleProps: DragHandleProps = { ...attributes, ...listeners };
  return renderItem(item, { setNodeRef, style, handleProps });
}
