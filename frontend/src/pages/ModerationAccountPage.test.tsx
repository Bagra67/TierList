import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { Account } from '../api/moderation';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { errorResponse, stubBackend } from '../test/stubBackend';
import { ModerationAccountPage } from './ModerationAccountPage';

const maxAccount: Account = {
  id: 'max-id',
  display_name: 'Max',
  email: 'max@example.com',
  created_at: '2026-10-01T12:00:00Z',
  email_verified: true,
  role: 'user',
  ban: null,
  templates: [
    {
      id: 'food-id',
      name: 'Food',
      tile_count: 12,
      updated_at: '2026-10-20T12:00:00Z',
      moderation: 'none',
      moderation_reason: null,
    },
    {
      id: 'teachers-id',
      name: 'Teachers',
      tile_count: 5,
      updated_at: '2026-10-21T12:00:00Z',
      moderation: 'hidden',
      moderation_reason: 'Harcèlement',
    },
  ],
};

interface Calls {
  imageQueries: URLSearchParams[];
  logQueries: URLSearchParams[];
  posts: { path: string; body: unknown }[];
}

function stubAccount(
  account: Account = maxAccount,
  postAnswer: () => Response = () => new Response(null, { status: 204 }),
): Calls {
  const calls: Calls = { imageQueries: [], logQueries: [], posts: [] };
  async function recordPost(request: Request): Promise<Response> {
    calls.posts.push({ path: new URL(request.url).pathname, body: await request.json() });
    return postAnswer();
  }
  stubBackend({
    'GET /moderation/accounts/max-id': () => Response.json(account),
    'GET /moderation/images': (request: Request) => {
      calls.imageQueries.push(new URL(request.url).searchParams);
      return Response.json({ images: [], has_more: false });
    },
    'GET /moderation/log': (request: Request) => {
      calls.logQueries.push(new URL(request.url).searchParams);
      return Response.json({ entries: [], has_more: false });
    },
    'POST /moderation/templates/food-id/hide': recordPost,
    'POST /moderation/templates/teachers-id/unhide': recordPost,
    'POST /moderation/accounts/max-id/hide-images': async (request: Request) => {
      calls.posts.push({ path: new URL(request.url).pathname, body: await request.json() });
      return Response.json({ hidden_count: 3 });
    },
  });
  return calls;
}

function renderAccountPage() {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={['/moderation/accounts/max-id']}>
      <Routes>
        <Route path="/moderation/accounts/:accountId" element={<ModerationAccountPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ModerationAccountPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('shows the details, the templates, the images and the history of the account', async () => {
    const calls: Calls = stubAccount();
    renderAccountPage();

    expect(await screen.findByRole('heading', { name: 'Max', level: 1 })).toBeInTheDocument();
    expect(screen.getByText('max@example.com')).toBeInTheDocument();
    const [food, teachers] = within(
      screen.getByRole('heading', { name: 'Modèles' }).parentElement as HTMLElement,
    ).getAllByRole('listitem');
    expect(within(food).getByRole('button', { name: 'Masquer le modèle Food' })).toBeVisible();
    expect(within(teachers).getByText('Masqué')).toBeInTheDocument();
    expect(
      within(teachers).getByRole('button', { name: 'Réafficher le modèle Teachers' }),
    ).toBeVisible();
    // Les images et l'historique sont lus filtrés sur ce compte
    await waitFor(() => expect(calls.imageQueries.at(-1)?.get('owner_id')).toBe('max-id'));
    await waitFor(() => expect(calls.logQueries.at(-1)?.get('account_id')).toBe('max-id'));
  });

  it('hides a template with a reason', async () => {
    const calls: Calls = stubAccount();
    renderAccountPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Masquer le modèle Food' }));
    const dialog = screen.getByRole('dialog', { name: 'Masquer le modèle « Food »' });
    fireEvent.change(within(dialog).getByLabelText('Motif'), { target: { value: 'Harcèlement' } });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Masquer' }));

    await waitFor(() =>
      expect(calls.posts).toEqual([
        { path: '/api/moderation/templates/food-id/hide', body: { reason: 'Harcèlement' } },
      ]),
    );
  });

  it('hides all the images of the account and says how many', async () => {
    const calls: Calls = stubAccount();
    renderAccountPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Masquer toutes ses images' }));
    const dialog = screen.getByRole('dialog', { name: 'Masquer toutes les images de Max' });
    fireEvent.change(within(dialog).getByLabelText('Motif'), { target: { value: 'Spam' } });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Tout masquer' }));

    expect(await screen.findByText('3 images masquées.')).toBeInTheDocument();
    expect(calls.posts).toEqual([
      { path: '/api/moderation/accounts/max-id/hide-images', body: { reason: 'Spam' } },
    ]);
  });

  it('says when the account does not exist', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    stubBackend({
      'GET /moderation/accounts/max-id': () => errorResponse(404, 'account_not_found'),
    });
    renderAccountPage();

    expect(await screen.findByRole('alert')).toHaveTextContent('Ce compte est introuvable.');
  });
});
