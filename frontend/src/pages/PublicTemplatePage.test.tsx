import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { PublicTemplate } from '../api/marketplace';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { errorResponse, stubBackend, type BackendMock } from '../test/stubBackend';
import { PublicTemplatePage } from './PublicTemplatePage';

const templateId: string = '5d0c2a8e-1f3b-4c7a-9e21-3a4b5c6d7e01';
const templateRoute: string = `GET /marketplace/templates/${templateId}`;

const chips: PublicTemplate = {
  id: templateId,
  name: 'Chips',
  owner_name: 'Camille',
  tags: ['apéro', 'snacks'],
  tiers: [
    { id: 'tier-s', name: 'S', color: '#FF3B6B', position: 0 },
    { id: 'tier-a', name: 'A', color: '#FF8A2A', position: 1 },
  ],
  tiles: [
    { id: 'tile-paprika', text: 'Paprika', image_url: null, image_removed: false },
    {
      id: 'tile-photo',
      text: null,
      image_url: 'https://images.example.com/photo.webp',
      image_removed: false,
    },
    { id: 'tile-removed', text: 'Nature', image_url: null, image_removed: true },
  ],
};

function renderPage(path: string = `/marketplace/templates/${templateId}`) {
  renderWithQueryClient(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/marketplace/templates/:templateId" element={<PublicTemplatePage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('PublicTemplatePage', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('shows a public template to a visitor: owner, tags, tiers and items', async () => {
    stubBackend({ [templateRoute]: () => Response.json(chips) });

    renderPage();

    expect(await screen.findByRole('heading', { level: 1, name: 'Chips' })).toBeInTheDocument();
    expect(screen.getByText('par Camille')).toBeInTheDocument();
    expect(document.title).toBe('Chips · TierList');
    const tags: HTMLElement = screen.getByRole('list', { name: 'Étiquettes du modèle' });
    expect(
      within(tags)
        .getAllByRole('listitem')
        .map((tag) => tag.textContent),
    ).toEqual(['apéro', 'snacks']);
    expect(screen.getByText('S')).toBeInTheDocument();
    expect(screen.getByText('A')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Éléments (3)' })).toBeInTheDocument();
    expect(screen.getByText('Paprika')).toBeInTheDocument();
    expect(screen.getByRole('img', { name: "Image de l'élément 2" })).toHaveAttribute(
      'src',
      'https://images.example.com/photo.webp',
    );
    expect(screen.getByText('Nature')).toBeInTheDocument();
  });

  it('says that a template without items has none', async () => {
    stubBackend({ [templateRoute]: () => Response.json({ ...chips, tiles: [] }) });

    renderPage();

    expect(
      await screen.findByText("Ce modèle n'a aucun élément pour l'instant."),
    ).toBeInTheDocument();
  });

  it('says that a template is not available without saying why', async () => {
    stubBackend({ [templateRoute]: () => errorResponse(404, 'template_not_found') });

    renderPage();

    expect(await screen.findByText("Ce modèle n'est pas disponible.")).toBeInTheDocument();
    expect(screen.getByRole('link', { name: "Retour à l'accueil" })).toHaveAttribute('href', '/');
    expect(document.title).toBe('Modèle indisponible · TierList');
  });

  it('says that a link that is not a template id is not available, without asking', () => {
    const fetchMock: BackendMock = stubBackend({});

    renderPage('/marketplace/templates/not-an-id');

    expect(screen.getByText("Ce modèle n'est pas disponible.")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('shows why the template cannot be read', async () => {
    stubBackend({ [templateRoute]: () => errorResponse(500, 'internal_error') });

    renderPage();

    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.queryByText("Ce modèle n'est pas disponible.")).not.toBeInTheDocument();
  });

  it('lets a visitor report the template', async () => {
    const fetchMock: BackendMock = stubBackend({
      [templateRoute]: () => Response.json(chips),
      'POST /reports': () => Response.json({ id: 'report-id' }, { status: 201 }),
    });
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Signaler : Chips' }));
    const dialog: HTMLElement = screen.getByRole('dialog', { name: 'Signaler ce modèle' });
    fireEvent.click(within(dialog).getByRole('radio', { name: 'Spam' }));
    fireEvent.click(within(dialog).getByRole('button', { name: 'Envoyer le signalement' }));

    const request: Request = await waitFor(() => {
      const call = fetchMock.mock.calls.find(([sent]) => sent.method === 'POST');
      if (call === undefined) throw new Error('No report sent yet');
      return call[0];
    });
    await expect(request.clone().json()).resolves.toMatchObject({
      target_kind: 'template',
      target_id: templateId,
      reason: 'spam',
    });
  });
});
