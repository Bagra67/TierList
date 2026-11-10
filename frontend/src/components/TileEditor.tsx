import { rectSortingStrategy } from '@dnd-kit/sortable';
import type { UseMutationResult } from '@tanstack/react-query';
import { ArrowLeft, ArrowRight, GripVertical, Trash2 } from 'lucide-react';
import { cn } from 'cn';
import { type FormEvent, type RefObject, useEffect, useId, useRef, useState } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import { type UploadedImage, useUploadImage } from '../api/images';
import {
  type NewTile,
  type Template,
  type TemplateChange,
  type Tile,
  type TileUpdate,
  useAddTile,
  useDeleteTile,
  useUpdateTile,
} from '../api/templates';
import { TILE_TEXT_MAX_LENGTH } from '../constants/templates';
import {
  getFieldErrors,
  hasNoFieldError,
  translateError,
  translateFieldError,
} from '../errors/apiError';
import { EMPHASIZED_BORDER_CLASS } from './boardStyles';
import { ErrorMessage } from './ErrorMessage';
import { ImageDropZone } from './ImageDropZone';
import { RemovedImageDecision } from './RemovedImageDecision';
import { InlineEditField } from './InlineEditField';
import { SortableList } from './SortableList';
import { TextField } from './TextField';
import { Button } from './ui/button';
import { type BulkImageTiles, type SkippedImage, useBulkImageTiles } from './useBulkImageTiles';

interface TileEditorProps {
  template: Template;
}

function hasImageEvenIfRemoved(tile: Tile): boolean {
  return tile.image_url !== null || tile.image_removed;
}

export function TileEditor({ template }: TileEditorProps) {
  const titleId: string = useId();
  const addFormRef: RefObject<HTMLFormElement | null> = useRef<HTMLFormElement>(null);
  const tileListRef: RefObject<HTMLOListElement | null> = useRef<HTMLOListElement>(null);
  const addMutation: TemplateChange<NewTile> = useAddTile(template.id);
  const updateMutation: TemplateChange<TileUpdate> = useUpdateTile(template.id);
  const deleteMutation: TemplateChange<string> = useDeleteTile(template.id);
  const newImageUpload: UseMutationResult<UploadedImage, Error, File> = useUploadImage();
  const tileImageUpload: UseMutationResult<UploadedImage, Error, File> = useUploadImage();
  const bulk = useBulkImageTiles(template);
  const [lastAddedTileIds, setLastAddedTileIds] = useState<string[]>([]);
  const [uploadedImageForNewTile, setUploadedImageForNewTile] = useState<UploadedImage | null>(
    null,
  );
  const [tileIdWithImageBeingSaved, setTileIdWithImageBeingSaved] = useState<string | null>(null);
  const [newTileLocalError, setNewTileLocalError] = useState<string | null>(null);
  const [tilesLocalError, setTilesLocalError] = useState<string | null>(null);
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const tiles: Tile[] = template.tiles;
  const isFull: boolean = tiles.length >= template.max_tiles;
  const isAddingImages: boolean = bulk.state?.isRunning ?? false;
  const isWaitingForOrderResponse: boolean = updateMutation.isPending || deleteMutation.isPending;
  const failedTileId: string | undefined = updateMutation.variables?.tileId;
  const textError: string | undefined = translateFieldError(
    t,
    getFieldErrors(updateMutation.error).text,
  );
  const newTextError: string | undefined = translateFieldError(
    t,
    getFieldErrors(addMutation.error).text,
  );
  const lastError: Error | null =
    updateMutation.error ?? deleteMutation.error ?? tileImageUpload.error;
  const showLastError: boolean = lastError !== null && hasNoFieldError(lastError);
  const newTileError: Error | null = addMutation.error ?? newImageUpload.error;
  const unsupportedImageMessage: string = t('errors.api.image_unsupported_format');

  useEffect(() => {
    const lastTileId: string | undefined = lastAddedTileIds.at(-1);
    if (lastTileId === undefined) return;
    const card: Element | null | undefined = tileListRef.current?.querySelector(
      `[data-tile-id="${lastTileId}"]`,
    );
    card?.scrollIntoView?.({ block: 'nearest' });
  }, [lastAddedTileIds]);

  function tileLabel(tile: Tile): string {
    return tile.text ?? t('templates.editor.tileName', { position: tile.position + 1 });
  }

  function clearTileErrors() {
    setTilesLocalError(null);
    updateMutation.reset();
    deleteMutation.reset();
    tileImageUpload.reset();
  }

  function moveTile(tile: Tile, position: number) {
    clearTileErrors();
    updateMutation.mutate({ tileId: tile.id, changes: { position } });
  }

  function deleteTile(tile: Tile) {
    clearTileErrors();
    deleteMutation.mutate(tile.id);
  }

  function saveTileText(tile: Tile, text: string) {
    const removesTheText: boolean = text.trim() === '' && hasImageEvenIfRemoved(tile);
    clearTileErrors();
    updateMutation.mutate({
      tileId: tile.id,
      changes: { text: removesTheText ? null : text },
    });
  }

  async function replaceTileImage(tile: Tile, file: File) {
    clearTileErrors();
    setTileIdWithImageBeingSaved(tile.id);
    try {
      const image: UploadedImage = await tileImageUpload.mutateAsync(file);
      await updateMutation.mutateAsync({ tileId: tile.id, changes: { image_id: image.id } });
    } catch {
      return;
    } finally {
      setTileIdWithImageBeingSaved(null);
    }
  }

  function removeTileImage(tile: Tile) {
    clearTileErrors();
    updateMutation.mutate({ tileId: tile.id, changes: { image_id: null } });
  }

  function chooseNewImage(file: File) {
    setNewTileLocalError(null);
    addMutation.reset();
    bulk.clear();
    newImageUpload.mutate(file, { onSuccess: setUploadedImageForNewTile });
  }

  async function addManyImages(files: File[]) {
    setNewTileLocalError(null);
    addMutation.reset();
    setLastAddedTileIds([]);
    setLastAddedTileIds(await bulk.addImages(files));
  }

  function removeNewImage() {
    setUploadedImageForNewTile(null);
    newImageUpload.reset();
  }

  async function handleAdd(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text: string = String(new FormData(event.currentTarget).get('text')).trim();
    if (text === '' && uploadedImageForNewTile === null) {
      setNewTileLocalError(t('errors.api.tile_empty'));
      return;
    }
    setNewTileLocalError(null);
    bulk.clear();
    setLastAddedTileIds([]);
    const newTile: NewTile = {};
    if (text !== '') newTile.text = text;
    if (uploadedImageForNewTile !== null) newTile.image_id = uploadedImageForNewTile.id;
    let updated: Template;
    try {
      updated = await addMutation.mutateAsync(newTile);
    } catch {
      return;
    }
    const added: Tile | undefined = updated.tiles.at(-1);
    if (added !== undefined) setLastAddedTileIds([added.id]);
    addFormRef.current?.reset();
    setUploadedImageForNewTile(null);
    newImageUpload.reset();
  }

  return (
    <section aria-labelledby={titleId} className="flex w-full flex-col gap-3 lg:min-h-0">
      <div className="flex items-baseline justify-between gap-4">
        <h2 id={titleId} className="text-lg font-semibold">
          {t('templates.editor.tiles')}
        </h2>
        <p className="text-sm text-muted-foreground">
          {t('templates.editor.tileCount', { count: tiles.length, max: template.max_tiles })}
        </p>
      </div>
      {tiles.length > 0 && (
        <ol
          ref={tileListRef}
          className="grid w-full grid-cols-2 gap-3 sm:grid-cols-3 lg:min-h-0 lg:flex-1 lg:content-start lg:overflow-y-auto lg:p-1 xl:grid-cols-4"
        >
          <SortableList
            items={tiles}
            strategy={rectSortingStrategy}
            getItemLabel={tileLabel}
            onMove={moveTile}
            disabled={isWaitingForOrderResponse}
            renderItem={(tile, { setNodeRef, style, handleProps }) => (
              <li
                ref={setNodeRef}
                style={style}
                data-tile-id={tile.id}
                className={cn(
                  'flex flex-col gap-2 rounded-md border bg-card p-2',
                  lastAddedTileIds.includes(tile.id) && EMPHASIZED_BORDER_CLASS,
                )}
              >
                <ImageDropZone
                  size="fullWidthSquare"
                  label={
                    !hasImageEvenIfRemoved(tile)
                      ? t('templates.editor.image.addTo', { name: tileLabel(tile) })
                      : t('templates.editor.image.replace', { name: tileLabel(tile) })
                  }
                  imageUrl={tile.image_url}
                  imageRemoved={tile.image_removed}
                  isUploading={tileIdWithImageBeingSaved === tile.id}
                  disabled={tileIdWithImageBeingSaved !== null}
                  removeLabel={
                    tile.text === null
                      ? undefined
                      : t('templates.editor.image.remove', { name: tileLabel(tile) })
                  }
                  onSelect={(file) => void replaceTileImage(tile, file)}
                  onRemove={() => removeTileImage(tile)}
                  onRefuse={() => setTilesLocalError(unsupportedImageMessage)}
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
                  error={failedTileId === tile.id ? textError : undefined}
                  onSave={(text) => saveTileText(tile, text)}
                />
                <div className="flex items-center justify-between">
                  <button
                    type="button"
                    {...handleProps}
                    aria-label={t('templates.editor.dragHandle', { name: tileLabel(tile) })}
                    className="cursor-grab touch-none rounded px-1 text-muted-foreground"
                  >
                    <GripVertical className="size-4" />
                  </button>
                  <div className="flex items-center">
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      aria-label={t('templates.editor.moveBefore', { name: tileLabel(tile) })}
                      disabled={isWaitingForOrderResponse || tile.position === 0}
                      onClick={() => moveTile(tile, tile.position - 1)}
                    >
                      <ArrowLeft />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      aria-label={t('templates.editor.moveAfter', { name: tileLabel(tile) })}
                      disabled={isWaitingForOrderResponse || tile.position === tiles.length - 1}
                      onClick={() => moveTile(tile, tile.position + 1)}
                    >
                      <ArrowRight />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      aria-label={t('templates.editor.deleteTile', { name: tileLabel(tile) })}
                      disabled={isWaitingForOrderResponse}
                      onClick={() => deleteTile(tile)}
                    >
                      <Trash2 />
                    </Button>
                  </div>
                </div>
              </li>
            )}
          />
        </ol>
      )}
      {tilesLocalError !== null && <ErrorMessage>{tilesLocalError}</ErrorMessage>}
      {tilesLocalError === null && showLastError && (
        <ErrorMessage>{translateError(t, lastError)}</ErrorMessage>
      )}
      <form ref={addFormRef} onSubmit={handleAdd} className="flex w-full flex-wrap items-end gap-3">
        <ImageDropZone
          size="addFormThumbnail"
          label={
            uploadedImageForNewTile === null
              ? t('templates.editor.image.addToNew')
              : t('templates.editor.image.replaceNew')
          }
          imageUrl={uploadedImageForNewTile?.url ?? null}
          isUploading={newImageUpload.isPending}
          disabled={isFull || isAddingImages}
          removeLabel={t('templates.editor.image.removeNew')}
          onSelect={chooseNewImage}
          onSelectMany={(files) => void addManyImages(files)}
          onRemove={removeNewImage}
          onRefuse={() => setNewTileLocalError(unsupportedImageMessage)}
        />
        <div className="flex min-w-48 flex-1 flex-col gap-1">
          <TextField
            label={t('templates.editor.newTileText')}
            name="text"
            maxLength={TILE_TEXT_MAX_LENGTH}
            disabled={isFull}
            error={newTextError}
          />
          <p className="text-xs text-muted-foreground">{t('templates.editor.newTileHint')}</p>
        </div>
        <Button
          type="submit"
          variant="outline"
          disabled={isFull || addMutation.isPending || newImageUpload.isPending || isAddingImages}
        >
          {addMutation.isPending ? t('templates.editor.addingTile') : t('templates.editor.addTile')}
        </Button>
      </form>
      {bulk.state !== null && <BulkImageTilesReport report={bulk.state} />}
      {isFull && (
        <p className="text-sm text-muted-foreground">
          {t('errors.api.tile_limit_reached', { max_tiles: template.max_tiles })}
        </p>
      )}
      {newTileLocalError !== null && <ErrorMessage>{newTileLocalError}</ErrorMessage>}
      {newTileLocalError === null && newTileError !== null && newTextError === undefined && (
        <ErrorMessage>{translateError(t, newTileError)}</ErrorMessage>
      )}
    </section>
  );
}

function BulkImageTilesReport({ report }: { report: BulkImageTiles }) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const progress: number = report.total === 0 ? 100 : (report.done / report.total) * 100;

  return (
    <div role="status" className="flex w-full flex-col gap-2 text-sm">
      {report.isRunning ? (
        <>
          <p>{t('templates.editor.bulk.progress', { done: report.done, total: report.total })}</p>
          <div className="h-1.5 w-full max-w-sm overflow-hidden rounded-full bg-muted">
            <div className="h-full rounded-full bg-primary" style={{ width: `${progress}%` }} />
          </div>
        </>
      ) : (
        <p className="font-medium">
          {t('templates.editor.bulk.added', { count: report.addedCount })}
        </p>
      )}
      {report.skipped.length > 0 && (
        <div className="flex flex-col gap-1 text-destructive">
          <p>{t('templates.editor.bulk.skipped', { count: report.skipped.length })}</p>
          <ul className="list-disc pl-5">
            {report.skipped.map((skippedImage: SkippedImage, index: number) => (
              <li key={`${skippedImage.fileName}-${index}`}>
                {t('templates.editor.bulk.skippedImage', {
                  name: skippedImage.fileName,
                  reason: skippedImage.reason,
                })}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
