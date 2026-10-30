import { useState } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import { type UploadedImage, uploadImage } from '../api/images';
import { type NewTile, type Template, type TemplateChange, useAddTile } from '../api/templates';
import { BULK_IMAGE_UPLOAD_CONCURRENCY } from '../constants/images';
import { translateError } from '../errors/apiError';
import { isAcceptedImageFile } from './imageFiles';

// Image du lot qui n'a pas donné de tuile, avec la raison, déjà traduite
export interface SkippedImage {
  fileName: string;
  reason: string;
}

export interface BulkImageTiles {
  // Images à envoyer, et combien sont traitées (ajoutées ou en échec)
  total: number;
  done: number;
  addedCount: number;
  skipped: SkippedImage[];
  isRunning: boolean;
}

// Envoi d'une image, toujours résolu : un échec attend son tour au lieu de rester une promesse
// rejetée que personne n'écoute encore
type UploadOutcome = { image: UploadedImage } | { error: unknown };

// Lance les envois limit par limit, dans l'ordre ; chaque promesse se résout à la fin de son envoi
function uploadAll(files: File[], limit: number): Promise<UploadOutcome>[] {
  let running: number = 0;
  const waiting: (() => void)[] = [];
  const takeTurn = (): Promise<void> => {
    if (running < limit) {
      running += 1;
      return Promise.resolve();
    }
    return new Promise<void>((resolve) => waiting.push(resolve));
  };
  const endTurn = (): void => {
    const next: (() => void) | undefined = waiting.shift();
    // Le tour passe directement au suivant : running ne change pas
    if (next === undefined) running -= 1;
    else next();
  };
  return files.map((file: File) =>
    takeTurn()
      .then(() => uploadImage(file))
      .then(
        (image: UploadedImage): UploadOutcome => ({ image }),
        (error: unknown): UploadOutcome => ({ error }),
      )
      .finally(endTurn),
  );
}

// Ajout de plusieurs images d'un coup (#242) : une tuile image (sans texte) par fichier, dans
// l'ordre de la sélection. Les images partent BULK_IMAGE_UPLOAD_CONCURRENCY à la fois par l'envoi
// habituel (POST /images : formats, taille, limite par heure), puis chaque tuile est créée à son
// tour. Un échec ne bloque pas les autres. Avant tout envoi, un type refusé et ce qui dépasse les
// places libres du modèle sont mis de côté
export function useBulkImageTiles(template: Template) {
  // Une mutation à part : ses erreurs vont dans le bilan, pas sous le formulaire d'ajout
  const addMutation: TemplateChange<NewTile> = useAddTile(template.id);
  const [state, setState] = useState<BulkImageTiles | null>(null);
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();

  // Renvoie les ids des tuiles ajoutées, dans l'ordre
  async function addImages(files: File[]): Promise<string[]> {
    const skipped: SkippedImage[] = [];
    const accepted: File[] = [];
    for (const file of files) {
      if (isAcceptedImageFile(file)) accepted.push(file);
      else skipped.push({ fileName: file.name, reason: t('errors.api.image_unsupported_format') });
    }
    const freeSlots: number = Math.max(0, template.max_tiles - template.tiles.length);
    const toSend: File[] = accepted.slice(0, freeSlots);
    for (const file of accepted.slice(freeSlots)) {
      skipped.push({
        fileName: file.name,
        reason: t('templates.editor.bulk.noRoom', { max_tiles: template.max_tiles }),
      });
    }

    let current: BulkImageTiles = {
      total: toSend.length,
      done: 0,
      addedCount: 0,
      skipped,
      isRunning: toSend.length > 0,
    };
    setState(current);
    const addedTileIds: string[] = [];
    const uploads: Promise<UploadOutcome>[] = uploadAll(toSend, BULK_IMAGE_UPLOAD_CONCURRENCY);
    for (const [index, file] of toSend.entries()) {
      const outcome: UploadOutcome = await uploads[index];
      let failure: unknown = 'error' in outcome ? outcome.error : null;
      if ('image' in outcome) {
        try {
          const updated: Template = await addMutation.mutateAsync({ image_id: outcome.image.id });
          // Une tuile ajoutée va en dernier
          const added: Template['tiles'][number] | undefined = updated.tiles.at(-1);
          if (added !== undefined) addedTileIds.push(added.id);
        } catch (error: unknown) {
          failure = error;
        }
      }
      current = {
        ...current,
        done: current.done + 1,
        addedCount: addedTileIds.length,
        skipped:
          failure === null
            ? current.skipped
            : [...current.skipped, { fileName: file.name, reason: translateError(t, failure) }],
        isRunning: index < toSend.length - 1,
      };
      setState(current);
    }
    return addedTileIds;
  }

  return { state, addImages, clear: () => setState(null) };
}
