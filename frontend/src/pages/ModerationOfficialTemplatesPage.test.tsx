import { fireEvent, screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { OfficialTemplateSummary } from '../api/officialTemplates';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { stubBackend } from '../test/stubBackend';
import { ModerationOfficialTemplatesPage } from './ModerationOfficialTemplatesPage';

const cheeses: OfficialTemplateSummary = {
  id: '5d0c2a8e-1f3b-4c7a-9e21-3a4b5c6d7e09',
  name: 'Fromages de France',
  tile_count: 12,
  updated_at: '2026-11-20T12:00:00Z',
  visibility: 'public',
  featured: true,
  editing_by_name: 'Camille',
};
const desserts: OfficialTemplateSummary = {
  id: '5d0c2a8e-1f3b-4c7a-9e21-3a4b5c6d7e10',
  name: 'Desserts du monde',
  tile_count: 1,
  updated_at: '2026-11-18T12:00:00Z',
  visibility: 'private',
  featured: false,
  editing_by_name: null,
};

function renderPage() {
  renderWithQueryClient(
    <MemoryRouter initialEntries={['/moderation/official-templates']}>
      <Routes>
        <Route
          path="/moderation/official-templates"
          element={<ModerationOfficialTemplatesPage />}
        />
        <Route path="/moderation/official-templates/:templateId" element={<h1>Éditeur</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ModerationOfficialTemplatesPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('lists the official templates with their state, pick badge and editor', async () => {
    stubBackend({
      'GET /moderation/official-templates': () => Response.json({ items: [cheeses, desserts] }),
    });

    renderPage();

    const rows: HTMLElement[] = await screen.findAllByRole('listitem');
    expect(within(rows[0]).getByRole('link', { name: 'Fromages de France' })).toHaveAttribute(
      'href',
      `/moderation/official-templates/${cheeses.id}`,
    );
    expect(within(rows[0]).getByText('Publié')).toBeInTheDocument();
    expect(within(rows[0]).getByText('Sélection TierList')).toBeInTheDocument();
    expect(within(rows[0]).getByText('Camille modifie ce modèle')).toBeInTheDocument();
    expect(within(rows[1]).getByText('Brouillon')).toBeInTheDocument();
    expect(within(rows[1]).getByText('1 élément')).toBeInTheDocument();
    expect(within(rows[1]).queryByText('Sélection TierList')).not.toBeInTheDocument();
  });

  it('says when there is no official template', async () => {
    stubBackend({ 'GET /moderation/official-templates': () => Response.json({ items: [] }) });

    renderPage();

    expect(await screen.findByText('Aucun modèle officiel pour l’instant.')).toBeInTheDocument();
  });

  it('creates an official template and opens it', async () => {
    stubBackend({
      'GET /moderation/official-templates': () => Response.json({ items: [] }),
      'POST /moderation/official-templates': () =>
        Response.json({ id: cheeses.id, name: 'Fromages de France' }, { status: 201 }),
    });

    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: 'Nouveau modèle officiel' }));
    const dialog: HTMLElement = screen.getByRole('dialog', { name: 'Nouveau modèle officiel' });
    fireEvent.change(within(dialog).getByLabelText('Nom'), {
      target: { value: 'Fromages de France' },
    });
    fireEvent.submit(within(dialog).getByRole('textbox'));

    expect(await screen.findByRole('heading', { name: 'Éditeur' })).toBeInTheDocument();
  });
});
