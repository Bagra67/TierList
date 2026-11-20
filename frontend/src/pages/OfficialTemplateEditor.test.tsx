import { fireEvent, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { Template } from '../api/templates';
import { OFFICIAL_TEMPLATE_LOCK_RENEW_MS } from '../constants/templates';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { alice, calledRoutes, errorResponse, stubBackend } from '../test/stubBackend';
import { TemplateEditorPage } from './TemplateEditorPage';

const templateId: string = '5d0c2a8e-1f3b-4c7a-9e21-3a4b5c6d7e09';
const templateUrl: string = `/templates/${templateId}`;
const lockUrl: string = `/moderation/official-templates/${templateId}/lock`;

const cheeses: Template = {
  id: templateId,
  name: 'Fromages de France',
  tags: [],
  created_at: '2026-11-20T12:00:00Z',
  updated_at: '2026-11-20T12:00:00Z',
  tiers: [{ id: 'tier-s', name: 'S', color: '#FF3B6B', position: 0 }],
  tiles: [
    {
      id: 'tile-comte',
      text: 'Comté',
      image_url: null,
      image_removed: false,
      image_status: null,
      image_moderation_reason: null,
      position: 0,
    },
  ],
  max_tiles: 256,
  max_tags: 20,
  moderation: 'none',
  moderation_reason: null,
  visibility: 'private',
  first_made_public_at: null,
  official: true,
  featured: false,
  editing_by_name: 'alice',
  editing_until: '2026-11-20T12:02:00Z',
};

function renderOfficialEditor() {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={[`/moderation/official-templates/${templateId}`]}>
      <Routes>
        <Route path="/moderation/official-templates/:templateId" element={<TemplateEditorPage />} />
        <Route path="/moderation/official-templates" element={<h1>Liste</h1>} />
      </Routes>
    </MemoryRouter>,
    { currentUser: { ...alice, role: 'super_admin' } },
  );
}

describe('TemplateEditorPage for an official template', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('takes the lease, shows the publishing panel and the official limits', async () => {
    const fetchMock = stubBackend({
      [`GET ${templateUrl}`]: () => Response.json(cheeses),
      [`POST ${lockUrl}`]: () => Response.json(cheeses),
    });

    renderOfficialEditor();

    expect(await screen.findByRole('heading', { name: 'Publication' })).toBeInTheDocument();
    expect(screen.getByText('Brouillon')).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: /Mettre en avant/ })).toBeDisabled();
    expect(screen.getByText("Publiez d'abord le modèle.")).toBeInTheDocument();
    expect(screen.getByText(/1 \/ 256/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Lancer une partie/ })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Modèles officiels' })).toHaveAttribute(
      'href',
      '/moderation/official-templates',
    );
    expect(calledRoutes(fetchMock)).toContain(`POST ${lockUrl}`);
  });

  it('publishes the draft, then lets it be featured', async () => {
    const fetchMock = stubBackend({
      [`GET ${templateUrl}`]: () => Response.json(cheeses),
      [`POST ${lockUrl}`]: () => Response.json(cheeses),
      [`POST /moderation/official-templates/${templateId}/publish`]: () =>
        Response.json({ ...cheeses, visibility: 'public' }),
    });

    renderOfficialEditor();
    fireEvent.click(await screen.findByRole('button', { name: 'Publier' }));

    expect(
      await screen.findByRole('button', { name: 'Repasser en brouillon' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: /Mettre en avant/ })).toBeEnabled();
    expect(calledRoutes(fetchMock)).toContain(
      `POST /moderation/official-templates/${templateId}/publish`,
    );
  });

  it('shows the template read-only with the name of the super admin editing it', async () => {
    stubBackend({
      [`GET ${templateUrl}`]: () => Response.json({ ...cheeses, editing_by_name: 'Camille' }),
      [`POST ${lockUrl}`]: () =>
        errorResponse(409, 'official_template_locked', { params: { editor: 'Camille' } }),
    });

    renderOfficialEditor();

    expect(await screen.findByText('Camille modifie ce modèle en ce moment.')).toBeInTheDocument();
    expect(screen.getByText('Comté')).toBeInTheDocument();
    expect(screen.queryByRole('textbox', { name: 'Nom du modèle' })).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Publication' })).not.toBeInTheDocument();
  });

  it('stops renewing the lease while the tab is hidden', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const fetchMock = stubBackend({
      [`GET ${templateUrl}`]: () => Response.json(cheeses),
      [`POST ${lockUrl}`]: () => Response.json(cheeses),
    });
    const visibility = vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden');

    renderOfficialEditor();
    await screen.findByRole('heading', { name: 'Publication' });
    await vi.advanceTimersByTimeAsync(OFFICIAL_TEMPLATE_LOCK_RENEW_MS * 2);

    expect(calledRoutes(fetchMock).filter((route) => route === `POST ${lockUrl}`)).toHaveLength(1);
    visibility.mockRestore();
    vi.useRealTimers();
  });

  it('gives the lease back when leaving the page', async () => {
    const fetchMock = stubBackend({
      [`GET ${templateUrl}`]: () => Response.json(cheeses),
      [`POST ${lockUrl}`]: () => Response.json(cheeses),
      [`DELETE ${lockUrl}`]: () => new Response(null, { status: 204 }),
    });

    const { unmount } = renderOfficialEditor();
    await screen.findByRole('heading', { name: 'Publication' });
    unmount();

    await waitFor(() => expect(calledRoutes(fetchMock)).toContain(`DELETE ${lockUrl}`));
  });
});
