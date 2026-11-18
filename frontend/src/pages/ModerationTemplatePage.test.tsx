import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { ReviewedTemplate } from '../api/moderation';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { calledRoutes, errorResponse, stubBackend, type BackendMock } from '../test/stubBackend';
import { ModerationTemplatePage } from './ModerationTemplatePage';

const template: ReviewedTemplate = {
  id: 'food-id',
  name: 'Food',
  updated_at: '2026-10-20T12:00:00Z',
  owner_id: 'max-id',
  owner_name: 'Max',
  moderation: 'none',
  moderation_reason: null,
  tiers: [
    { id: 'tier-s', name: 'S', color: '#FF7F7F', position: 0 },
    { id: 'tier-a', name: 'A', color: '#FFBF7F', position: 1 },
  ],
  tiles: [
    { id: 'tile-text', text: 'Paprika', image_url: null, image_status: null },
    {
      id: 'tile-visible',
      text: null,
      image_url: 'https://images.example.com/visible.webp',
      image_status: 'visible',
    },
    {
      id: 'tile-hidden',
      text: null,
      image_url: 'https://images.example.com/quarantine.webp',
      image_status: 'hidden',
    },
    { id: 'tile-deleted', text: 'Curry', image_url: null, image_status: 'deleted' },
  ],
};

function renderPage(routes: Parameters<typeof stubBackend>[0]): BackendMock {
  const fetchMock: BackendMock = stubBackend(routes);
  renderWithQueryClient(
    <MemoryRouter initialEntries={['/moderation/templates/food-id']}>
      <Routes>
        <Route path="/moderation/templates/:templateId" element={<ModerationTemplatePage />} />
        <Route path="/moderation/accounts/:accountId" element={<h1>Page du compte</h1>} />
      </Routes>
    </MemoryRouter>,
  );
  return fetchMock;
}

const readsTemplate = { 'GET /moderation/templates/food-id': () => Response.json(template) };

describe('ModerationTemplatePage', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('shows the owner, the tiers and the tiles of the template', async () => {
    renderPage(readsTemplate);

    expect(await screen.findByRole('heading', { name: 'Food', level: 1 })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Max' })).toHaveAttribute(
      'href',
      '/moderation/accounts/max-id',
    );
    expect(screen.getByText('S')).toBeInTheDocument();
    expect(screen.getByText('A')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '4 tuiles' })).toBeInTheDocument();
    expect(screen.getByText('Paprika')).toBeInTheDocument();
  });

  it('shows a hidden image with a mention, and a deleted image as removed', async () => {
    renderPage(readsTemplate);

    expect(await screen.findByRole('img', { name: 'Image de la tuile 3' })).toHaveAttribute(
      'src',
      'https://images.example.com/quarantine.webp',
    );
    expect(screen.getAllByText('Image masquée par la modération')).toHaveLength(1);
    expect(screen.getByRole('img', { name: 'Image de la tuile 2' })).toHaveAttribute(
      'src',
      'https://images.example.com/visible.webp',
    );
    expect(screen.getByRole('img', { name: 'Image retirée' })).toBeInTheDocument();
    expect(screen.getByText('Curry')).toBeInTheDocument();
  });

  it('shows a hidden template with its reason, which can be shown again', async () => {
    renderPage({
      'GET /moderation/templates/food-id': () =>
        Response.json({ ...template, moderation: 'hidden', moderation_reason: 'Harcèlement' }),
    });

    expect(await screen.findByText('Motif : Harcèlement')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Réafficher' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Masquer' })).not.toBeInTheDocument();
  });

  it('says when the template has no tile', async () => {
    renderPage({
      'GET /moderation/templates/food-id': () => Response.json({ ...template, tiles: [] }),
    });

    expect(await screen.findByText("Ce modèle n'a aucune tuile.")).toBeInTheDocument();
  });

  it('shows why the template cannot be read', async () => {
    renderPage({
      'GET /moderation/templates/food-id': () => errorResponse(404, 'template_not_found'),
    });

    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });

  it('hides the template with a reason and stays on the page', async () => {
    const fetchMock: BackendMock = renderPage({
      ...readsTemplate,
      'POST /moderation/templates/food-id/hide': () => new Response(null, { status: 204 }),
    });

    fireEvent.click(await screen.findByRole('button', { name: 'Masquer' }));
    const dialog: HTMLElement = screen.getByRole('dialog', { name: 'Masquer le modèle « Food »' });
    fireEvent.change(within(dialog).getByLabelText('Motif'), { target: { value: 'Illicite' } });
    fireEvent.click(within(dialog).getByRole('button', { name: /^Masquer/ }));

    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(([call]) => new URL(call.url).pathname.endsWith('/hide')),
      ).toBe(true),
    );
    expect(await screen.findByRole('heading', { name: 'Food', level: 1 })).toBeInTheDocument();
  });

  it('goes back to the account after deleting the template, without reading it again', async () => {
    const fetchMock: BackendMock = renderPage({
      ...readsTemplate,
      'POST /moderation/templates/food-id/delete': () => new Response(null, { status: 204 }),
    });

    fireEvent.click(await screen.findByRole('button', { name: 'Supprimer' }));
    const dialog: HTMLElement = screen.getByRole('dialog', {
      name: 'Supprimer le modèle « Food »',
    });
    fireEvent.change(within(dialog).getByLabelText('Motif'), { target: { value: 'Illicite' } });
    fireEvent.click(within(dialog).getByRole('button', { name: /^Supprimer/ }));

    expect(await screen.findByRole('heading', { name: 'Page du compte' })).toBeInTheDocument();
    expect(
      calledRoutes(fetchMock).filter((route) => route === 'GET /moderation/templates/food-id'),
    ).toHaveLength(1);
  });
});
