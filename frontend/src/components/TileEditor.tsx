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
import { getFieldErrors, translateError, translateFieldError } from '../errors/apiError';
import { EMPHASIZED_BORDER_CLASS } from './boardStyles';
import { ErrorMessage } from './ErrorMessage';
import { ImageDropZone } from './ImageDropZone';
import { InlineEditField } from './InlineEditField';
import { SortableList } from './SortableList';
import { TextField } from './TextField';
import { Button } from './ui/button';
import { type BulkImageTiles, type SkippedImage, useBulkImageTiles } from './useBulkImageTiles';

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
  const tileListRef: RefObject<HTMLOListElement | null> = useRef<HTMLOListElement>(null);
  const addMutation: TemplateChange<NewTile> = useAddTile(template.id);
  const updateMutation: TemplateChange<TileUpdate> = useUpdateTile(template.id);
  const deleteMutation: TemplateChange<string> = useDeleteTile(template.id);
  const newImageUpload: UseMutationResult<UploadedImage, Error, File> = useUploadImage();
  const tileImageUpload: UseMutationResult<UploadedImage, Error, File> = useUploadImage();
  // Plusieurs images déposées d'un coup sur la vignette de la nouvelle tuile (#242)
  const bulk = useBulkImageTiles(template);
  // Tuiles du dernier ajout (une seule, ou tout un lot) : mises en avant jusqu'au suivant
  const [lastAddedTileIds, setLastAddedTileIds] = useState<string[]>([]);
  // Image envoyée pour la tuile en cours d'ajout, rattachée à l'ajout
  const [newImage, setNewImage] = useState<UploadedImage | null>(null);
  // Tuile dont l'image est en cours d'envoi puis d'enregistrement
  const [imageTileId, setImageTileId] = useState<string | null>(null);
  // Erreurs vues avant tout envoi (fichier refusé, tuile vide), une par zone ; celle des tuiles
  // disparaît à la prochaine action sur une tuile
  const [newTileLocalError, setNewTileLocalError] = useState<string | null>(null);
  const [tilesLocalError, setTilesLocalError] = useState<string | null>(null);
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const tiles: Tile[] = template.tiles;
  const isFull: boolean = tiles.length >= template.max_tiles;
  const isAddingImages: boolean = bulk.state?.isRunning ?? false;
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

  // La dernière tuile ajoutée défile dans la vue quand la grille défile (grand écran)
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

  function moveTile(tile: Tile, position: number) {
    setTilesLocalError(null);
    updateMutation.mutate({ tileId: tile.id, changes: { position } });
  }

  function deleteTile(tile: Tile) {
    setTilesLocalError(null);
    deleteMutation.mutate(tile.id);
  }

  // Une tuile qui a une image peut perdre son texte : un texte vidé part en null. Sans image, le
  // texte est envoyé tel quel : le backend le refuse, et l'erreur s'affiche sous le champ
  function saveTileText(tile: Tile, text: string) {
    const removesTheText: boolean = text.trim() === '' && tile.image_url !== null;
    setTilesLocalError(null);
    updateMutation.mutate({
      tileId: tile.id,
      changes: { text: removesTheText ? null : text },
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
    bulk.clear();
    newImageUpload.mutate(file, { onSuccess: setNewImage });
  }

  // Plusieurs images d'un coup : une tuile par image, sans passer par le formulaire
  async function addManyImages(files: File[]) {
    setNewTileLocalError(null);
    addMutation.reset();
    setLastAddedTileIds([]);
    setLastAddedTileIds(await bulk.addImages(files));
  }

  // Retire aussi l'erreur d'un envoi précédent : elle ne concerne plus l'image affichée
  function removeNewImage() {
    setNewImage(null);
    newImageUpload.reset();
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
    bulk.clear();
    setLastAddedTileIds([]);
    // Seuls les champs renseignés sont envoyés
    const newTile: NewTile = {};
    if (text !== '') newTile.text = text;
    if (newImage !== null) newTile.image_id = newImage.id;
    let updated: Template;
    try {
      updated = await addMutation.mutateAsync(newTile);
    } catch {
      return; // l'erreur est affichée depuis addMutation.error
    }
    // Une tuile ajoutée va en dernier
    const added: Tile | undefined = updated.tiles.at(-1);
    if (added !== undefined) setLastAddedTileIds([added.id]);
    addFormRef.current?.reset();
    setNewImage(null);
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
        // Grand écran : seule la grille défile, le compteur et le formulaire d'ajout restent
        // visibles. content-start : les rangées gardent leur hauteur au lieu de s'étirer
        <ol
          ref={tileListRef}
          className="grid w-full grid-cols-2 gap-3 sm:grid-cols-3 lg:min-h-0 lg:flex-1 lg:content-start lg:overflow-y-auto lg:p-1 xl:grid-cols-4"
        >
          <SortableList
            items={tiles}
            strategy={rectSortingStrategy}
            getItemLabel={tileLabel}
            onMove={moveTile}
            disabled={isChangingOrder}
            renderItem={(tile, { setNodeRef, style, handleProps }) => (
              // Carte : l'image sur toute la largeur, son texte dessous, puis les actions
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
                  size="fill"
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
                  multiline
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
                      disabled={isChangingOrder || tile.position === 0}
                      onClick={() => moveTile(tile, tile.position - 1)}
                    >
                      <ArrowLeft />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      aria-label={t('templates.editor.moveAfter', { name: tileLabel(tile) })}
                      disabled={isChangingOrder || tile.position === tiles.length - 1}
                      onClick={() => moveTile(tile, tile.position + 1)}
                    >
                      <ArrowRight />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      aria-label={t('templates.editor.deleteTile', { name: tileLabel(tile) })}
                      disabled={isChangingOrder}
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
          size="large"
          label={
            newImage === null
              ? t('templates.editor.image.addToNew')
              : t('templates.editor.image.replaceNew')
          }
          imageUrl={newImage?.url ?? null}
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

// Progression puis bilan d'un ajout de plusieurs images : combien de tuiles ont été ajoutées, et
// chaque image ignorée avec sa raison. Un seul status : les lecteurs d'écran lisent l'avancée
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
