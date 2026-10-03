import { vi } from 'vitest';

import type { ErrorResponse } from '../errors/apiError';

// Réponse simulée d'une route, à partir de la requête reçue (pour lire ses en-têtes ou son corps)
export type StubbedRoute = (request: Request) => Response | Promise<Response>;

// Remplace fetch par un faux backend : clés « MÉTHODE /chemin » (sans le préfixe /api).
// Une route non déclarée répond 404, pour qu'un appel inattendu fasse échouer le test.
export function stubBackend(routes: Record<string, StubbedRoute>) {
  const fetchMock = vi.fn(async (request: Request) => {
    const path = new URL(request.url).pathname.replace(/^\/api/, '');
    const route = routes[`${request.method} ${path}`];
    return route ? route(request) : errorResponse(404, 'http_error');
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

// Requêtes reçues par le faux backend, sous la forme « MÉTHODE /chemin »
export function calledRoutes(fetchMock: ReturnType<typeof stubBackend>): string[] {
  return fetchMock.mock.calls.map(
    ([request]) => `${request.method} ${new URL(request.url).pathname.replace(/^\/api/, '')}`,
  );
}

// Réponse d'erreur au format ErrorResponse du backend : l'interface traduit `code`, jamais `detail`
export function errorResponse(
  status: number,
  code: string,
  extra: Pick<ErrorResponse, 'params' | 'errors'> = {},
): Response {
  return Response.json({ detail: `${code} (detail)`, code, ...extra }, { status });
}

export const unauthorized = () => errorResponse(401, 'not_authenticated');

export const tokenResponse = (accessToken: string) => () =>
  Response.json({ access_token: accessToken, token_type: 'bearer', expires_in: 900 });

export const alice = {
  id: '0b6f3c1e-6d5c-4c1e-9f57-6d1c7e1f0a01',
  email: 'alice@example.com',
  display_name: 'Alice',
  has_password: true,
  email_verified: true,
  created_at: '2026-10-03T10:00:00Z',
};
