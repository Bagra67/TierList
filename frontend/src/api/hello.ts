import { useQuery } from '@tanstack/react-query';

import { ApiError, apiClient } from './client';
import type { components } from './schema';

// Généré depuis le schéma Pydantic HelloResponse du backend (pnpm gen:api) : jamais recopié à la main
export type HelloResponse = components['schemas']['HelloResponse'];

export async function getHello(signal?: AbortSignal): Promise<HelloResponse> {
  const { data, error, response } = await apiClient.GET('/hello', { signal });
  if (data === undefined) {
    throw new ApiError(response.status, error);
  }
  return data;
}

export function useHello() {
  return useQuery({
    queryKey: ['hello'],
    queryFn: ({ signal }) => getHello(signal),
  });
}
