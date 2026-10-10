import { rectSortingStrategy } from '@dnd-kit/sortable';
import type { UseMutationResult } from '@tanstack/react-query';
import { type FormEvent, type RefObject, useId, useRef, useState } from 'react';
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
import { getFieldErrors, translateError, translateFieldError } from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { ImageDropZone } from './ImageDropZone';
import { InlineEditField } from './InlineEditField';
import { SortableList } from './SortableList';
import { TextField } from './TextField';
import { Button } from './ui/button';

interface TileEditorProps {
  template: Template;
}

// Tuiles d'un template (US-1.2, US-1.3), dans l'ordre du template : un texte, une image, ou les
// deux. Chaque action est enregistrée tout de suite ; une image est envoyée dès qu'elle est
// choisie (le backend la compresse), puis rattachée à la tuile. Le nombre maximal vient du
// backend (max_tiles).
export function TileEditor({ template }: TileEditorProps) {
  const titleId: string = useId();
  const addFormRef: RefObject<HTMLFormElement | null> = useRef<HTMLFormElement>(null);
  const addMutation: TemplateChange<NewTile> = useAddTile(template.id);
  const updateMutation: TemplateChange<TileUpdate> = useUpdateTile(template.id);
  const deleteMutation: TemplateChange<string> = useDeleteTile(template.id);
  const newImageUpload: UseMutationResult<UploadedImage, Error, File> = useUploadImage();
  const tileImageUpload: UseMutationResult<UploadedImage, Error, File> = useUploadImage();
  // Image envoyée pour la tuile en cours d'ajout, rattachée à l'ajout
  const [newImage, setNewImage] = useState<UploadedImage | null>(null);
  // Tuile dont l'image est en cours d'envoi puis d'enregistrement
  const [imageTileId, setImageTileId] = useState<string | null>(null);
  // Erreurs vues avant tout envoi (fichier refusé, tuile vide), une par zone
  const [newTileLocalError, setNewTileLocalError] = useState<string | null>(null);
  const [tilesLocalError, setTilesLocalError] = useState<string | null>(null);
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const tiles: Tile[] = template.tiles;
  const isFull: boolean = tiles.length >= template.max_tiles;
  // Une seule modification de l'ordre à la fois : les réponses arrivent dans l'ordre des clics
  const isChangingOrder: boolean = updateMutation.isPending || deleteMutation.isPending;
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
  // Une erreur de champ (422) s'affiche déjà sous son champ : pas de second message
  const showLastError: boolean =
    lastError !== null && Object.keys(getFieldErrors(lastError)).length === 0;
  const newTileError: Error | null = addMutation.error ?? newImageUpload.error;
  const unsupportedImageMessage: string = t('errors.api.image_unsupported_format');

  function tileLabel(tile: Tile): string {
    return tile.text ?? t('templates.editor.tileName', { position: tile.position + 1 });
  }

  function moveTile(tile: Tile, position: number) {
    updateMutation.mutate({ tileId: tile.id, changes: { position } });
  }

  // Un texte vidé veut dire « plus de texte » : le backend refuse si la tuile n'a pas d'image
  function saveTileText(tile: Tile, text: string) {
    const trimmedText: string = text.trim();
    updateMutation.mutate({
      tileId: tile.id,
      changes: { text: trimmedText === '' ? null : text },
    });
  }

  async function replaceTileImage(tile: Tile, file: File) {
    setTilesLocalError(null);
    setImageTileId(tile.id);
    try {
      const image: UploadedImage = await tileImageUpload.mutateAsync(file);
      await updateMutation.mutateAsync({ tileId: tile.id, changes: { image_id: image.id } });
    } catch {
      // l'erreur est affichée depuis tileImageUpload.error ou updateMutation.error
    } finally {
      setImageTileId(null);
    }
  }

  function removeTileImage(tile: Tile) {
    setTilesLocalError(null);
    updateMutation.mutate({ tileId: tile.id, changes: { image_id: null } });
  }

  function chooseNewImage(file: File) {
    setNewTileLocalError(null);
    addMutation.reset();
    newImageUpload.mutate(file, { onSuccess: setNewImage });
  }

  async function handleAdd(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text: string = String(new FormData(event.currentTarget).get('text')).trim();
    if (text === '' && newImage === null) {
      // Le backend le refuserait aussi (tile_empty) : inutile de l'interroger
      setNewTileLocalError(t('errors.api.tile_empty'));
      return;
    }
    setNewTileLocalError(null);
    // Seuls les champs renseignés sont envoyés
    const newTile: NewTile = {};
    if (text !== '') newTile.text = text;
    if (newImage !== null) newTile.image_id = newImage.id;
    try {
      await addMutation.mutateAsync(newTile);
    } catch {
      return; // l'erreur est affichée depuis addMutation.error
    }
    addFormRef.current?.reset();
    setNewImage(null);
    newImageUpload.reset();
  }

  return (
    <section aria-labelledby={titleId} className="flex w-full flex-col gap-3">
      <div className="flex items-baseline justify-between gap-4">
        <h2 id={titleId} className="text-lg font-semibold">
          {t('templates.editor.tiles')}
        </h2>
        <p className="text-sm text-muted-foreground">
          {t('templates.editor.tileCount', { count: tiles.length, max: template.max_tiles })}
        </p>
      </div>
      {tiles.length > 0 && (
        <ol className="grid w-full grid-cols-1 gap-2 sm:grid-cols-2">
          <SortableList
            items={tiles}
            strategy={rectSortingStrategy}
            getItemLabel={tileLabel}
            onMove={moveTile}
            disabled={isChangingOrder}
            renderItem={(tile, { setNodeRef, style, handleProps }) => (
              <li
                ref={setNodeRef}
                style={style}
                className="flex items-center gap-2 rounded-md border bg-card px-2 py-2"
              >
                <button
                  type="button"
                  {...handleProps}
                  aria-label={t('templates.editor.dragHandle', { name: tileLabel(tile) })}
                  className="cursor-grab touch-none rounded px-1 text-muted-foreground"
                >
                  <span aria-hidden="true">⋮⋮</span>
                </button>
                <ImageDropZone
                  size="small"
                  label={
                    tile.image_url === null
                      ? t('templates.editor.image.addTo', { name: tileLabel(tile) })
                      : t('templates.editor.image.replace', { name: tileLabel(tile) })
                  }
                  imageUrl={tile.image_url}
                  isUploading={imageTileId === tile.id}
                  disabled={imageTileId !== null}
                  // Sans texte, retirer l'image laisserait la tuile vide : pas de bouton
                  removeLabel={
                    tile.text === null
                      ? undefined
                      : t('templates.editor.image.remove', { name: tileLabel(tile) })
                  }
                  onSelect={(file) => void replaceTileImage(tile, file)}
                  onRemove={() => removeTileImage(tile)}
                  onRefuse={() => setTilesLocalError(unsupportedImageMessage)}
                />
                <InlineEditField
                  key={tile.text ?? ''}
                  label={t('templates.editor.tileText', { position: tile.position + 1 })}
                  hideLabel
                  value={tile.text ?? ''}
                  maxLength={TILE_TEXT_MAX_LENGTH}
                  required={tile.image_url === null}
                  error={failedTileId === tile.id ? textError : undefined}
                  onSave={(text) => saveTileText(tile, text)}
                  className="flex-1"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  aria-label={t('templates.editor.moveBefore', { name: tileLabel(tile) })}
                  disabled={isChangingOrder || tile.position === 0}
                  onClick={() => moveTile(tile, tile.position - 1)}
                >
                  <span aria-hidden="true">←</span>
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  aria-label={t('templates.editor.moveAfter', { name: tileLabel(tile) })}
                  disabled={isChangingOrder || tile.position === tiles.length - 1}
                  onClick={() => moveTile(tile, tile.position + 1)}
                >
                  <span aria-hidden="true">→</span>
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  aria-label={t('templates.editor.deleteTile', { name: tileLabel(tile) })}
                  disabled={isChangingOrder}
                  onClick={() => deleteMutation.mutate(tile.id)}
                >
                  <span aria-hidden="true">✕</span>
                </Button>
              </li>
            )}
          />
        </ol>
      )}
      {tilesLocalError !== null && <ErrorMessage>{tilesLocalError}</ErrorMessage>}
      {tilesLocalError === null && showLastError && (
        <ErrorMessage>{translateError(t, lastError)}</ErrorMessage>
      )}
      <form ref={addFormRef} onSubmit={handleAdd} className="flex w-full items-end gap-3">
        <ImageDropZone
          size="large"
          label={
            newImage === null
              ? t('templates.editor.image.addToNew')
              : t('templates.editor.image.replaceNew')
          }
          imageUrl={newImage?.url ?? null}
          isUploading={newImageUpload.isPending}
          disabled={isFull}
          removeLabel={t('templates.editor.image.removeNew')}
          onSelect={chooseNewImage}
          onRemove={() => setNewImage(null)}
          onRefuse={() => setNewTileLocalError(unsupportedImageMessage)}
        />
        <div className="flex flex-1 flex-col gap-1">
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
          disabled={isFull || addMutation.isPending || newImageUpload.isPending}
        >
          {addMutation.isPending ? t('templates.editor.addingTile') : t('templates.editor.addTile')}
        </Button>
      </form>
      {/* La limite est vérifiée par le backend ; l'interface l'annonce avant qu'on essaie */}
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
