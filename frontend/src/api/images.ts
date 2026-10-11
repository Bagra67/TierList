import { type UseMutationResult, useMutation } from '@tanstack/react-query';

import { apiClient, dataOrThrow } from './client';
import type { components } from './schema';

// Image compressée par le backend : son id se donne ensuite à une tuile (image_id)
export type UploadedImage = components['schemas']['ImageUploadResponse'];

async function uploadImage(file: File): Promise<UploadedImage> {
  return dataOrThrow(
    await apiClient.POST('/images', {
      // Le schéma décrit le fichier comme une chaîne binaire : le vrai fichier part dans un
      // FormData, dont le navigateur écrit lui-même le Content-Type (avec sa frontière)
      body: { file: file.name },
      bodySerializer: () => {
        const formData: FormData = new FormData();
        formData.append('file', file);
        return formData;
      },
    }),
  );
}

export function useUploadImage(): UseMutationResult<UploadedImage, Error, File> {
  return useMutation({ mutationFn: uploadImage });
}
