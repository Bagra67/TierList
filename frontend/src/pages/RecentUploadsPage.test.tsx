import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { RecentUpload, RecentUploadsPage as UploadsPage } from '../api/moderation';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { errorResponse, stubBackend } from '../test/stubBackend';
import { RecentUploadsPage } from './RecentUploadsPage';

function renderUploadsPage() {
  return renderWithQueryClient(
    <MemoryRouter>
      <RecentUploadsPage />
    </MemoryRouter>,
  );
}

function upload(overrides: Partial<RecentUpload>): RecentUpload {
  return {
    id: 'image-1',
    url: 'https://images.example.com/image-1.webp',
    status: 'visible',
    created_at: '2026-10-31T18:42:00Z',
    author_name: 'Camille',
    template_names: ['Desserts', 'Food'],
    game_count: 3,
    ...overrides,
  };
}

interface StubbedUploads {
  queries: URLSearchParams[];
  moderations: { path: string; body: unknown }[];
}

// Le faux backend renvoie la page selon l'offset demandé, garde les paramètres reçus et les
// actions de modération envoyées
function stubUploads(
  pages: Record<string, UploadsPage>,
  moderationAnswer: () => Response = () => new Response(null, { status: 204 }),
): StubbedUploads {
  const stubbed: StubbedUploads = { queries: [], moderations: [] };
  async function recordModeration(request: Request): Promise<Response> {
    stubbed.moderations.push({
      path: new URL(request.url).pathname,
      body: await request.json(),
    });
    return moderationAnswer();
  }
  stubBackend({
    'GET /moderation/images': (request: Request) => {
      const query: URLSearchParams = new URL(request.url).searchParams;
      stubbed.queries.push(query);
      return Response.json(pages[query.get('offset') ?? ''] ?? { images: [], has_more: false });
    },
    'POST /moderation/images/image-1/hide': recordModeration,
    'POST /moderation/images/image-1/unhide': recordModeration,
    'POST /moderation/images/image-1/delete': recordModeration,
  });
  return stubbed;
}

describe('RecentUploadsPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('shows each image with its author, date and use', async () => {
    stubUploads({ '0': { images: [upload({})], has_more: false } });
    renderUploadsPage();

    const image = await screen.findByRole('img', { name: /Image envoyée par Camille/ });
    expect(image).toHaveAttribute('src', 'https://images.example.com/image-1.webp');
    const card = image.closest('li') as HTMLElement;
    expect(card).toHaveTextContent('2 modèles · 3 parties');
    expect(card).toHaveTextContent('Modèles : Desserts et Food');
    expect(within(card).getByRole('button', { name: /Masquer l'image de Camille/ })).toBeVisible();
    expect(
      within(card).getByRole('button', { name: /Supprimer l'image de Camille/ }),
    ).toBeVisible();
    expect(within(card).queryByText('Masquée')).not.toBeInTheDocument();
  });

  it('marks a hidden image, which can be unhidden, and names a deleted account', async () => {
    stubUploads({
      '0': {
        images: [
          upload({ status: 'hidden', author_name: null, template_names: [], game_count: 1 }),
        ],
        has_more: false,
      },
    });
    renderUploadsPage();

    const card = (await screen.findByText('Masquée')).closest('li') as HTMLElement;
    expect(card).toHaveTextContent('Compte supprimé');
    expect(card).toHaveTextContent('0 modèle · 1 partie');
    expect(
      within(card).getByRole('button', { name: /Réafficher l'image de Compte supprimé/ }),
    ).toBeVisible();
    expect(within(card).queryByRole('button', { name: /^Masquer/ })).not.toBeInTheDocument();
  });

  it('says when nothing was uploaded, and when nothing matches the filters', async () => {
    stubUploads({});
    renderUploadsPage();

    expect(await screen.findByText("Aucune image n'a encore été envoyée.")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Statut'), { target: { value: 'hidden' } });

    expect(
      await screen.findByText('Aucune image ne correspond à ces filtres.'),
    ).toBeInTheDocument();
  });

  it('sends the author, the days and the status as filters', async () => {
    const stubbed: StubbedUploads = stubUploads({});
    renderUploadsPage();
    await screen.findByText("Aucune image n'a encore été envoyée.");

    fireEvent.change(screen.getByLabelText('Auteur'), { target: { value: ' camille ' } });
    fireEvent.click(screen.getByRole('button', { name: 'Rechercher' }));
    fireEvent.change(screen.getByLabelText('Du'), { target: { value: '2026-10-01' } });
    fireEvent.change(screen.getByLabelText('Au'), { target: { value: '2026-10-31' } });
    fireEvent.change(screen.getByLabelText('Statut'), { target: { value: 'visible' } });

    await waitFor(() => expect(stubbed.queries.at(-1)?.get('status')).toBe('visible'));
    const query: URLSearchParams = stubbed.queries.at(-1) as URLSearchParams;
    expect(query.get('author')).toBe('camille');
    // Les jours choisis, dans le fuseau du super admin : le dernier est inclus en entier
    expect(query.get('created_after')).toBe(new Date('2026-10-01T00:00:00').toISOString());
    expect(query.get('created_before')).toBe(new Date('2026-11-01T00:00:00').toISOString());
  });

  it('loads the next page on demand', async () => {
    const stubbed: StubbedUploads = stubUploads({
      '0': { images: [upload({})], has_more: true },
      '1': { images: [upload({ id: 'image-2', author_name: 'Noé' })], has_more: false },
    });
    renderUploadsPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Voir plus' }));

    expect(await screen.findByRole('img', { name: /Image envoyée par Noé/ })).toBeVisible();
    expect(stubbed.queries.map((query) => query.get('offset'))).toEqual(['0', '1']);
    expect(screen.queryByRole('button', { name: 'Voir plus' })).not.toBeInTheDocument();
  });

  it('hides an image with a reason, then reads the uploads again', async () => {
    const stubbed: StubbedUploads = stubUploads({ '0': { images: [upload({})], has_more: false } });
    renderUploadsPage();

    fireEvent.click(await screen.findByRole('button', { name: /Masquer l'image de Camille/ }));
    const dialog = screen.getByRole('dialog', { name: 'Masquer cette image' });
    fireEvent.change(within(dialog).getByLabelText('Motif'), { target: { value: ' Violence ' } });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Masquer' }));

    await waitFor(() => expect(stubbed.queries).toHaveLength(2));
    expect(stubbed.moderations).toEqual([
      { path: '/api/moderation/images/image-1/hide', body: { reason: 'Violence' } },
    ]);
  });

  it('shows why a moderation action failed', async () => {
    stubUploads({ '0': { images: [upload({})], has_more: false } }, () =>
      errorResponse(409, 'image_moderation_conflict'),
    );
    renderUploadsPage();

    fireEvent.click(await screen.findByRole('button', { name: /Supprimer l'image de Camille/ }));
    const dialog = screen.getByRole('dialog', { name: 'Supprimer cette image' });
    fireEvent.change(within(dialog).getByLabelText('Motif'), { target: { value: 'Spam' } });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Supprimer' }));

    expect(await within(dialog).findByRole('alert')).toHaveTextContent(
      "Cette action ne s'applique pas à l'image dans son état actuel",
    );
  });
});
