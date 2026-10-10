import { rectSortingStrategy } from '@dnd-kit/sortable';
import { useId, useRef, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import {
  type Template,
  type Tile,
  useAddTile,
  useDeleteTile,
  useUpdateTile,
} from '../api/templates';
import { TILE_TEXT_MAX_LENGTH } from '../constants/templates';
import { getFieldErrors, translateError, translateFieldError } from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { InlineEditField } from './InlineEditField';
import { SortableList } from './SortableList';
import { TextField } from './TextField';
import { Button } from './ui/button';

interface TileEditorProps {
  template: Template;
}

// Tuiles texte d'un template (US-1.2, US-1.3), dans l'ordre du template : chaque action est
// enregistrée tout de suite. Le nombre maximal vient du backend (max_tiles).
export function TileEditor({ template }: TileEditorProps) {
  const titleId = useId();
  const addFormRef = useRef<HTMLFormElement>(null);
  const addMutation = useAddTile(template.id);
  const updateMutation = useUpdateTile(template.id);
  const deleteMutation = useDeleteTile(template.id);
  const { t } = useTranslation();
  const tiles: Tile[] = template.tiles;
  const isFull = tiles.length >= template.max_tiles;
  // Une seule modification de l'ordre à la fois : les réponses arrivent dans l'ordre des clics
  const isChangingOrder = updateMutation.isPending || deleteMutation.isPending;
  const failedTileId = updateMutation.variables?.tileId;
  const textError = translateFieldError(t, getFieldErrors(updateMutation.error).text);
  const newTextError = translateFieldError(t, getFieldErrors(addMutation.error).text);
  const lastError = updateMutation.error ?? deleteMutation.error;

  function tileLabel(tile: Tile): string {
    return tile.text ?? t('templates.editor.tileText', { position: tile.position + 1 });
  }

  function moveTile(tile: Tile, position: number) {
    updateMutation.mutate({ tileId: tile.id, changes: { position } });
  }

  async function handleAdd(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = String(new FormData(event.currentTarget).get('text'));
    try {
      await addMutation.mutateAsync(text);
    } catch {
      return; // l'erreur est affichée depuis addMutation.error
    }
    addFormRef.current?.reset();
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
            renderItem={(tile, { setNodeRef, style, handleProps }) => (
              <li
                ref={setNodeRef}
                style={style}
                className="flex items-start gap-1 rounded-md border bg-card px-2 py-2"
              >
                <button
                  type="button"
                  {...handleProps}
                  aria-label={t('templates.editor.dragHandle', { name: tileLabel(tile) })}
                  className="mt-1 cursor-grab touch-none rounded px-1 text-muted-foreground"
                >
                  <span aria-hidden="true">⋮⋮</span>
                </button>
                <InlineEditField
                  key={tile.text}
                  label={t('templates.editor.tileText', { position: tile.position + 1 })}
                  hideLabel
                  value={tile.text ?? ''}
                  maxLength={TILE_TEXT_MAX_LENGTH}
                  error={failedTileId === tile.id ? textError : undefined}
                  onSave={(text) => updateMutation.mutate({ tileId: tile.id, changes: { text } })}
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
      {lastError !== null && <ErrorMessage>{translateError(t, lastError)}</ErrorMessage>}
      <form ref={addFormRef} onSubmit={handleAdd} className="flex w-full items-end gap-2">
        <div className="flex-1">
          <TextField
            label={t('templates.editor.newTileText')}
            name="text"
            required
            maxLength={TILE_TEXT_MAX_LENGTH}
            disabled={isFull}
            error={newTextError}
          />
        </div>
        <Button type="submit" variant="outline" disabled={isFull || addMutation.isPending}>
          {addMutation.isPending ? t('templates.editor.addingTile') : t('templates.editor.addTile')}
        </Button>
      </form>
      {/* La limite est vérifiée par le backend ; l'interface l'annonce avant qu'on essaie */}
      {isFull && (
        <p className="text-sm text-muted-foreground">
          {t('errors.api.tile_limit_reached', { max_tiles: template.max_tiles })}
        </p>
      )}
      {addMutation.isError && newTextError === undefined && (
        <ErrorMessage>{translateError(t, addMutation.error)}</ErrorMessage>
      )}
    </section>
  );
}
