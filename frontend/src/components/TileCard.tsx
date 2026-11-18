import { ArrowLeft, ArrowRight, GripVertical, Trash2 } from 'lucide-react';
import { cn } from 'cn';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { Tile } from '../api/templates';
import { TILE_TEXT_MAX_LENGTH } from '../constants/templates';
import { EMPHASIZED_BORDER_CLASS } from './boardStyles';
import { ImageDropZone } from './ImageDropZone';
import { hasImageEvenIfRemoved } from './tileImage';
import { InlineEditField } from './InlineEditField';
import { RemovedImageDecision } from './RemovedImageDecision';
import type { SortableRender } from './SortableList';
import { Button } from './ui/button';

interface TileCardProps {
  tile: Tile;
  label: string;
  setNodeRef: SortableRender['setNodeRef'];
  sortableStyle: SortableRender['style'];
  handleProps: SortableRender['handleProps'];
  emphasized: boolean;
  isLast: boolean;
  orderLocked: boolean;
  imageBeingSaved: boolean;
  imageLocked: boolean;
  textError: string | undefined;
  onReplaceImage: (file: File) => void;
  onRemoveImage: () => void;
  onRefuseImage: () => void;
  onSaveText: (text: string) => void;
  onMove: (position: number) => void;
  onDelete: () => void;
}

export function TileCard({
  tile,
  label,
  setNodeRef,
  sortableStyle,
  handleProps,
  emphasized,
  isLast,
  orderLocked,
  imageBeingSaved,
  imageLocked,
  textError,
  onReplaceImage,
  onRemoveImage,
  onRefuseImage,
  onSaveText,
  onMove,
  onDelete,
}: TileCardProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();

  return (
    <li
      ref={setNodeRef}
      style={sortableStyle}
      data-tile-id={tile.id}
      className={cn(
        'flex flex-col gap-2 rounded-md border bg-card p-2',
        emphasized && EMPHASIZED_BORDER_CLASS,
      )}
    >
      <ImageDropZone
        size="fullWidthSquare"
        label={
          !hasImageEvenIfRemoved(tile)
            ? t('templates.editor.image.addTo', { name: label })
            : t('templates.editor.image.replace', { name: label })
        }
        imageUrl={tile.image_url}
        imageRemoved={tile.image_removed}
        isUploading={imageBeingSaved}
        disabled={imageLocked}
        removeLabel={
          tile.text === null ? undefined : t('templates.editor.image.remove', { name: label })
        }
        onSelect={onReplaceImage}
        onRemove={onRemoveImage}
        onRefuse={onRefuseImage}
      />
      {tile.image_removed && (
        <RemovedImageDecision
          status={tile.image_status === 'deleted' ? 'deleted' : 'hidden'}
          reason={tile.image_moderation_reason}
        />
      )}
      <InlineEditField
        key={tile.text ?? ''}
        label={t('templates.editor.tileText', { position: tile.position + 1 })}
        hideLabel
        value={tile.text ?? ''}
        maxLength={TILE_TEXT_MAX_LENGTH}
        required={!hasImageEvenIfRemoved(tile)}
        wrapsLongValue
        error={textError}
        onSave={onSaveText}
      />
      <div className="flex items-center justify-between">
        <button
          type="button"
          {...handleProps}
          aria-label={t('templates.editor.dragHandle', { name: label })}
          className="cursor-grab touch-none rounded px-1 text-muted-foreground"
        >
          <GripVertical className="size-4" />
        </button>
        <div className="flex items-center">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label={t('templates.editor.moveBefore', { name: label })}
            disabled={orderLocked || tile.position === 0}
            onClick={() => onMove(tile.position - 1)}
          >
            <ArrowLeft />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label={t('templates.editor.moveAfter', { name: label })}
            disabled={orderLocked || isLast}
            onClick={() => onMove(tile.position + 1)}
          >
            <ArrowRight />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label={t('templates.editor.deleteTile', { name: label })}
            disabled={orderLocked}
            onClick={onDelete}
          >
            <Trash2 />
          </Button>
        </div>
      </div>
    </li>
  );
}
