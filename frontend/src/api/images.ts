import { type UseMutationResult, useMutation } from '@tanstack/react-query';

import { apiClient, dataOrThrow } from './client';
import type { components } from './schema';

export type UploadedImage = components['schemas']['ImageUploadResponse'];

function formDataWithContentTypeLeftToBrowser(file: File): FormData {
  const formData: FormData = new FormData();
  formData.append('file', file);
  return formData;
}

export async function uploadImage(file: File): Promise<UploadedImage> {
  const bodyOnlyForSchemaTyping: string = file.name;
  return dataOrThrow(
    await apiClient.POST('/images', {
      body: { file: bodyOnlyForSchemaTyping },
      bodySerializer: () => formDataWithContentTypeLeftToBrowser(file),
    }),
  );
}

export function useUploadImage(): UseMutationResult<UploadedImage, Error, File> {
  return useMutation({ mutationFn: uploadImage });
}
