import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { TemplateSummary } from '../api/templates';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { calledRoutes, errorResponse, stubBackend } from '../test/stubBackend';
import { TemplatesPage } from './TemplatesPage';

const chips: TemplateSummary = {
  id: '5d0c2a8e-1f3b-4c7a-9e21-3a4b5c6d7e01',
  name: 'Chips',
  tile_count: 12,
  // Midi UTC : la même date quel que soit le fuseau de la machine de test
  updated_at: '2026-10-05T12:00:00Z',
};
const sodas: TemplateSummary = {
  id: '5d0c2a8e-1f3b-4c7a-9e21-3a4b5c6d7e02',
  name: 'Sodas',
  tile_count: 1,
  updated_at: '2026-10-04T12:00:00Z',
};

const createdTemplate = {
  id: '5d0c2a8e-1f3b-4c7a-9e21-3a4b5c6d7e03',
  name: 'Fromages',
  created_at: '2026-10-06T12:00:00Z',
  updated_at: '2026-10-06T12:00:00Z',
  tiers: [],
  tiles: [],
};

// L'éditeur est remplacé par un simple titre : seule la navigation vers lui est vérifiée ici
function renderTemplatesPage() {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={['/templates']}>
      <Routes>
        <Route path="/templates" element={<TemplatesPage />} />
        <Route path="/templates/:templateId" element={<h1>Éditeur</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

const listOf = (templates: TemplateSummary[]) => () => Response.json({ items: templates });

describe('TemplatesPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('lists the templates with their tile count and last change date', async () => {
    stubBackend({ 'GET /templates': listOf([chips, sodas]) });

    renderTemplatesPage();

    expect(screen.getByText('Chargement…')).toBeInTheDocument();
    const items = await screen.findAllByRole('listitem');
    expect(items).toHaveLength(2);
    expect(within(items[0]).getByRole('link', { name: 'Chips' })).toHaveAttribute(
      'href',
      `/templates/${chips.id}`,
    );
    expect(items[0]).toHaveTextContent('12 tuiles');
    expect(items[0]).toHaveTextContent('Modifié le 5 octobre 2026');
    expect(items[1]).toHaveTextContent('1 tuile');
  });

  it('invites to create a template when there is none', async () => {
    stubBackend({ 'GET /templates': listOf([]) });

    renderTemplatesPage();

    expect(await screen.findByText(/aucun template/)).toBeInTheDocument();
    expect(screen.queryByRole('list')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Nouveau template' })).toBeInTheDocument();
  });

  it('shows an error when the list cannot be loaded', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    stubBackend({ 'GET /templates': () => errorResponse(500, 'internal_error') });

    renderTemplatesPage();

    expect(await screen.findByRole('alert')).toHaveTextContent('Erreur interne du serveur');
    consoleError.mockRestore();
  });

  it('creates a template and opens it in the editor', async () => {
    const fetchMock = stubBackend({
      'GET /templates': listOf([]),
      'POST /templates': () => Response.json(createdTemplate, { status: 201 }),
    });
    renderTemplatesPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Nouveau template' }));
    const dialog = screen.getByRole('dialog', { name: 'Nouveau template' });
    fireEvent.change(within(dialog).getByLabelText('Nom'), { target: { value: 'Fromages' } });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Créer' }));

    expect(await screen.findByRole('heading', { name: 'Éditeur' })).toBeInTheDocument();
    const createCall = fetchMock.mock.calls.find(([request]) => request.method === 'POST');
    await expect(createCall?.[0].json()).resolves.toEqual({ name: 'Fromages' });
  });

  it('shows the field error when the name is blank', async () => {
    stubBackend({
      'GET /templates': listOf([]),
      'POST /templates': () =>
        errorResponse(422, 'validation_error', {
          errors: [
            {
              field: 'body.name',
              message: 'String should have at least 1 character',
              code: 'string_too_short',
              params: { min_length: 1 },
            },
          ],
        }),
    });
    renderTemplatesPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Nouveau template' }));
    const dialog = screen.getByRole('dialog', { name: 'Nouveau template' });
    fireEvent.change(within(dialog).getByLabelText('Nom'), { target: { value: '   ' } });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Créer' }));

    expect(await within(dialog).findByText('Au moins 1 caractères.')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('Nom')).toHaveAttribute('aria-invalid', 'true');
    expect(dialog).toBeVisible();
    expect(screen.queryByRole('heading', { name: 'Éditeur' })).not.toBeInTheDocument();
  });

  it('deletes a template after confirmation and refreshes the list', async () => {
    let templates = [chips, sodas];
    const fetchMock = stubBackend({
      'GET /templates': () => Response.json({ items: templates }),
      [`DELETE /templates/${chips.id}`]: () => {
        templates = [sodas];
        return new Response(null, { status: 204 });
      },
    });
    renderTemplatesPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Supprimer Chips' }));
    const dialog = screen.getByRole('dialog', { name: 'Supprimer « Chips » ?' });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Supprimer' }));

    await waitFor(() => expect(screen.queryByText('Chips')).not.toBeInTheDocument());
    expect(screen.getByText('Sodas')).toBeInTheDocument();
    expect(calledRoutes(fetchMock)).toEqual([
      'GET /templates',
      `DELETE /templates/${chips.id}`,
      'GET /templates',
    ]);
  });

  it('keeps the template when the deletion is cancelled', async () => {
    const fetchMock = stubBackend({ 'GET /templates': listOf([chips]) });
    renderTemplatesPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Supprimer Chips' }));
    const dialog = screen.getByRole('dialog', { name: 'Supprimer « Chips » ?' });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Annuler' }));

    expect(dialog).not.toBeVisible();
    expect(screen.getByText('Chips')).toBeInTheDocument();
    expect(calledRoutes(fetchMock)).toEqual(['GET /templates']);
  });

  it('shows an error when the template to delete no longer exists', async () => {
    stubBackend({
      'GET /templates': listOf([chips]),
      [`DELETE /templates/${chips.id}`]: () => errorResponse(404, 'template_not_found'),
    });
    renderTemplatesPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Supprimer Chips' }));
    const dialog = screen.getByRole('dialog', { name: 'Supprimer « Chips » ?' });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Supprimer' }));

    expect(await within(dialog).findByRole('alert')).toHaveTextContent(
      'Ce template est introuvable.',
    );
  });
});
