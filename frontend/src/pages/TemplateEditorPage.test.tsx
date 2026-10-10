import { screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { Template } from '../api/templates';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { errorResponse, stubBackend } from '../test/stubBackend';
import { TemplateEditorPage } from './TemplateEditorPage';

const templateId = '5d0c2a8e-1f3b-4c7a-9e21-3a4b5c6d7e01';

const chips: Template = {
  id: templateId,
  name: 'Chips',
  created_at: '2026-10-05T12:00:00Z',
  updated_at: '2026-10-05T12:00:00Z',
  tiers: [
    { id: 't-s', name: 'S', color: '#FF7F7F', position: 0 },
    { id: 't-a', name: 'A', color: '#FFBF7F', position: 1 },
  ],
  tiles: [],
};

function renderEditor() {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={[`/templates/${templateId}`]}>
      <Routes>
        <Route path="/templates/:templateId" element={<TemplateEditorPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('TemplateEditorPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('shows the template name and its tiers in order', async () => {
    stubBackend({ [`GET /templates/${templateId}`]: () => Response.json(chips) });

    renderEditor();

    expect(await screen.findByRole('heading', { name: 'Chips' })).toBeInTheDocument();
    const tiers = within(screen.getByRole('region', { name: 'Tiers' })).getAllByRole('listitem');
    expect(tiers.map((tier) => tier.textContent)).toEqual(['S', 'A']);
    expect(screen.getByRole('link', { name: 'Retour à mes templates' })).toHaveAttribute(
      'href',
      '/templates',
    );
  });

  it('shows an error when the template does not exist', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    stubBackend({
      [`GET /templates/${templateId}`]: () => errorResponse(404, 'template_not_found'),
    });

    renderEditor();

    expect(await screen.findByRole('alert')).toHaveTextContent('Ce template est introuvable.');
    consoleError.mockRestore();
  });
});
