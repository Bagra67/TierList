import { vi } from 'vitest';

import type { User } from '../api/auth';
import type { ErrorResponse } from '../errors/apiError';

export type StubbedRoute = (request: Request) => Response | Promise<Response>;

export function stubBackend(routes: Record<string, StubbedRoute>) {
  const fetchMock = vi.fn(async (request: Request) => {
    const path = new URL(request.url).pathname.replace(/^\/api/, '');
    const route = routes[`${request.method} ${path}`];
    return route ? route(request) : errorResponse(404, 'http_error');
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

export type BackendMock = ReturnType<typeof stubBackend>;

export function calledRoutes(fetchMock: BackendMock): string[] {
  return fetchMock.mock.calls.map(
    ([request]) => `${request.method} ${new URL(request.url).pathname.replace(/^\/api/, '')}`,
  );
}

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

export const alice: User = {
  id: '0b6f3c1e-6d5c-4c1e-9f57-6d1c7e1f0a01',
  email: 'alice@example.com',
  display_name: 'Alice',
  has_password: true,
  email_verified: true,
  role: 'user',
  created_at: '2026-10-03T10:00:00Z',
};

export const signedInSession: Record<string, StubbedRoute> = {
  'POST /auth/refresh': tokenResponse('alice-token'),
  'GET /auth/me': () => Response.json(alice),
};

export const superAdminSession: Record<string, StubbedRoute> = {
  ...signedInSession,
  'GET /auth/me': () => Response.json({ ...alice, role: 'super_admin' } satisfies User),
};
