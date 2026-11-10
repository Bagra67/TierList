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
  past_bans: [],
  templates: [
    {
      id: 'food-id',
      name: 'Food',
      tile_count: 12,
      updated_at: '2026-10-20T12:00:00Z',
      moderation: 'none',
      moderation_reason: null,
      removed_images: [],
    },
    {
      id: 'teachers-id',
      name: 'Teachers',
      tile_count: 5,
      updated_at: '2026-10-21T12:00:00Z',
      moderation: 'hidden',
      moderation_reason: 'Harcèlement',
      removed_images: [],
    },
  ],
};

interface Calls {
  reportQueries: URLSearchParams[];
  imageQueries: URLSearchParams[];
  logQueries: URLSearchParams[];
  posts: { path: string; body: unknown }[];
}

function stubAccount(
  account: Account = maxAccount,
  postAnswer: () => Response = () => new Response(null, { status: 204 }),
): Calls {
  const calls: Calls = { reportQueries: [], imageQueries: [], logQueries: [], posts: [] };
  async function recordPost(request: Request): Promise<Response> {
    calls.posts.push({ path: new URL(request.url).pathname, body: await request.json() });
    return postAnswer();
  }
  stubBackend({
    'GET /moderation/accounts/max-id': () => Response.json(account),
    'GET /moderation/reports': (request: Request) => {
      calls.reportQueries.push(new URL(request.url).searchParams);
      return Response.json({
        contents: [
          {
            target_type: 'nickname',
            target_id: 'max-id',
            label: 'Max le spammeur',
            owner_id: 'max-id',
            owner_name: 'Max',
            report_count: 1,
            reasons: [{ reason: 'spam', count: 1 }],
            details: [],
            first_reported_at: '2026-10-20T12:00:00Z',
            image_url: null,
            public_token: null,
          },
        ],
        has_more: false,
      });
    },
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
      const batches: number = calls.posts.length;
      return Response.json({ hidden_count: batches === 1 ? 2 : 1, has_more: batches === 1 });
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
    await waitFor(() => expect(calls.imageQueries.at(-1)?.get('owner_id')).toBe('max-id'));
    await waitFor(() => expect(calls.logQueries.at(-1)?.get('account_id')).toBe('max-id'));
  });

  it('links each template to its content, even a hidden one', async () => {
    stubAccount();
    renderAccountPage();

    expect(await screen.findByRole('link', { name: 'Food' })).toHaveAttribute(
      'href',
      '/moderation/templates/food-id',
    );
    expect(screen.getByRole('link', { name: 'Teachers' })).toHaveAttribute(
      'href',
      '/moderation/templates/teachers-id',
    );
  });

  it('shows the reports on the content of the account', async () => {
    const calls: Calls = stubAccount();
    renderAccountPage();

    expect(
      await screen.findByRole('heading', { name: 'Signalements sur ses contenus' }),
    ).toBeInTheDocument();
    expect(await screen.findByText('Max le spammeur')).toBeInTheDocument();
    expect(calls.reportQueries[0].get('owner_id')).toBe('max-id');
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

  it('hides all the images of the account batch by batch, says how many and reads its reports again', async () => {
    const calls: Calls = stubAccount();
    renderAccountPage();
    await screen.findByText('Max le spammeur');

    fireEvent.click(await screen.findByRole('button', { name: 'Masquer toutes ses images' }));
    const dialog = screen.getByRole('dialog', { name: 'Masquer toutes les images de Max' });
    fireEvent.change(within(dialog).getByLabelText('Motif'), { target: { value: 'Spam' } });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Tout masquer' }));

    expect(await screen.findByText('3 images masquées.')).toBeInTheDocument();
    expect(calls.posts).toEqual([
      { path: '/api/moderation/accounts/max-id/hide-images', body: { reason: 'Spam' } },
      { path: '/api/moderation/accounts/max-id/hide-images', body: { reason: 'Spam' } },
    ]);
    await waitFor(() => expect(calls.reportQueries).toHaveLength(2));
  });

  it('stops hiding when a batch hides nothing, even if more is announced', async () => {
    let hideRequests: number = 0;
    stubBackend({
      'GET /moderation/accounts/max-id': () => Response.json(maxAccount),
      'GET /moderation/reports': () => Response.json({ contents: [], has_more: false }),
      'GET /moderation/images': () => Response.json({ images: [], has_more: false }),
      'GET /moderation/log': () => Response.json({ entries: [], has_more: false }),
      'POST /moderation/accounts/max-id/hide-images': () => {
        hideRequests += 1;
        return Response.json({ hidden_count: 0, has_more: true });
      },
    });
    renderAccountPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Masquer toutes ses images' }));
    const dialog = screen.getByRole('dialog', { name: 'Masquer toutes les images de Max' });
    fireEvent.change(within(dialog).getByLabelText('Motif'), { target: { value: 'Spam' } });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Tout masquer' }));

    expect(await screen.findByText('0 image masquée.')).toBeInTheDocument();
    expect(hideRequests).toBe(1);
  });

  it('shows an active ban, which can be lifted with a reason', async () => {
    const calls: Calls = { reportQueries: [], imageQueries: [], logQueries: [], posts: [] };
    stubBackend({
      'GET /moderation/accounts/max-id': () =>
        Response.json({
          ...maxAccount,
          ban: {
            created_at: '2026-10-30T12:00:00Z',
            ends_at: null,
            reason: 'Harcèlement répété',
            actor_name: 'Nina',
          },
        }),
      'GET /moderation/images': () => Response.json({ images: [], has_more: false }),
      'GET /moderation/log': () => Response.json({ entries: [], has_more: false }),
      'POST /moderation/accounts/max-id/lift-ban': async (request: Request) => {
        calls.posts.push({ path: new URL(request.url).pathname, body: await request.json() });
        return new Response(null, { status: 204 });
      },
    });
    renderAccountPage();

    expect(await screen.findByText('Banni définitivement')).toBeInTheDocument();
    expect(screen.getByText('Motif : Harcèlement répété')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Lever le bannissement' }));
    const dialog = screen.getByRole('dialog', { name: 'Lever le bannissement de Max' });
    fireEvent.change(within(dialog).getByLabelText('Motif'), { target: { value: 'Recours' } });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Lever le bannissement' }));

    await waitFor(() =>
      expect(calls.posts).toEqual([
        { path: '/api/moderation/accounts/max-id/lift-ban', body: { reason: 'Recours' } },
      ]),
    );
  });

  it('lists the past bans of the account', async () => {
    stubAccount({
      ...maxAccount,
      past_bans: [
        {
          created_at: '2026-10-10T12:00:00Z',
          ends_at: '2026-10-20T12:00:00Z',
          lifted_at: null,
          reason: 'Spam',
          actor_name: 'Nina',
        },
        {
          created_at: '2026-09-01T12:00:00Z',
          ends_at: null,
          lifted_at: '2026-09-05T12:00:00Z',
          reason: 'Harcèlement',
          actor_name: 'Omar',
        },
      ],
    });
    renderAccountPage();

    const heading: HTMLElement = await screen.findByRole('heading', {
      name: 'Bannissements passés',
    });
    const items: HTMLElement[] = within(heading.parentElement as HTMLElement).getAllByRole(
      'listitem',
    );
    expect(items[0]).toHaveTextContent(/Banni le 10 oct\. 2026, jusqu.au 20 oct\. 2026/);
    expect(items[0]).toHaveTextContent('Motif : Spam');
    expect(items[1]).toHaveTextContent(/levé ou remplacé le 5 sept\. 2026/);
    expect(items[1]).toHaveTextContent('Par Omar');
  });

  it('shows no past bans section for an account never banned', async () => {
    stubAccount();
    renderAccountPage();

    await screen.findByRole('heading', { name: 'Bannissement' });
    expect(screen.queryByRole('heading', { name: 'Bannissements passés' })).toBeNull();
  });

  it('offers to ban a user but never a super admin', async () => {
    stubAccount({ ...maxAccount, role: 'super_admin' });
    renderAccountPage();

    expect(await screen.findByText('Un super admin ne peut pas être banni.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Bannir ce compte' })).not.toBeInTheDocument();
  });

  it('says when the account does not exist', async () => {
    stubBackend({
      'GET /moderation/accounts/max-id': () => errorResponse(404, 'account_not_found'),
    });
    renderAccountPage();

    expect(await screen.findByRole('alert')).toHaveTextContent('Ce compte est introuvable.');
  });
});
