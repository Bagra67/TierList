import { useState } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import { type UploadedImage, uploadImage } from '../api/images';
import { type NewTile, type Template, type TemplateChange, useAddTile } from '../api/templates';
import { BULK_IMAGE_UPLOAD_CONCURRENCY } from '../constants/images';
import { translateError } from '../errors/apiError';
import { isAcceptedImageFile } from './imageFiles';

export interface SkippedImage {
  fileName: string;
  reason: string;
}

export interface BulkImageTiles {
  total: number;
  done: number;
  addedCount: number;
  skipped: SkippedImage[];
  isRunning: boolean;
}

type UploadOutcome = { image: UploadedImage } | { error: unknown };

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

export function useBulkImageTiles(template: Template) {
  const addMutationForBulkSummary: TemplateChange<NewTile> = useAddTile(template.id);
  const [state, setState] = useState<BulkImageTiles | null>(null);
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();

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
          const updated: Template = await addMutationForBulkSummary.mutateAsync({
            image_id: outcome.image.id,
          });
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
