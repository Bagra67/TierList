import { rectSortingStrategy } from '@dnd-kit/sortable';
import type { UseMutationResult } from '@tanstack/react-query';
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
import { ErrorMessage } from './ErrorMessage';
import { ImageDropZone } from './ImageDropZone';
import { SortableList } from './SortableList';
import { TextField } from './TextField';
import { Button } from './ui/button';
import { BulkImageTilesReport } from './BulkImageTilesReport';
import { TileCard } from './TileCard';
import { hasImageEvenIfRemoved } from './tileImage';
import { useBulkImageTiles } from './useBulkImageTiles';

interface TileEditorProps {
  template: Template;
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
              <TileCard
                tile={tile}
                label={tileLabel(tile)}
                setNodeRef={setNodeRef}
                sortableStyle={style}
                handleProps={handleProps}
                emphasized={lastAddedTileIds.includes(tile.id)}
                isLast={tile.position === tiles.length - 1}
                orderLocked={isWaitingForOrderResponse}
                imageBeingSaved={tileIdWithImageBeingSaved === tile.id}
                imageLocked={tileIdWithImageBeingSaved !== null}
                textError={failedTileId === tile.id ? textError : undefined}
                onReplaceImage={(file: File) => void replaceTileImage(tile, file)}
                onRemoveImage={() => removeTileImage(tile)}
                onRefuseImage={() => setTilesLocalError(unsupportedImageMessage)}
                onSaveText={(text: string) => saveTileText(tile, text)}
                onMove={(position: number) => moveTile(tile, position)}
                onDelete={() => deleteTile(tile)}
              />
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
