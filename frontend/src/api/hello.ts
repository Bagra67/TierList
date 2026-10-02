import type { components } from './schema';

// Généré depuis le schéma Pydantic HelloResponse du backend (pnpm gen:api) : jamais recopié à la main
export type HelloResponse = components['schemas']['HelloResponse'];

// '/api' est redirigé vers le backend FastAPI par le proxy Vite (vite.config.ts)
export async function getHello(signal?: AbortSignal): Promise<HelloResponse> {
  const response = await fetch('/api/hello', { signal });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json() as Promise<HelloResponse>;
}
