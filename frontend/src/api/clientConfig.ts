import { apiClient, dataOrThrow } from './client';
import type { components } from './schema';

export type ClientConfig = components['schemas']['ClientConfigResponse'];

export async function getClientConfig(): Promise<ClientConfig> {
  return dataOrThrow(await apiClient.GET('/client-config'));
}
