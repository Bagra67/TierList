import { act, fireEvent, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, type MockInstance, vi } from 'vitest';

import type { Template, TemplateSummary } from '../api/templates';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { aliceRoom } from '../test/fixtures/rooms';
import {
  calledRoutes,
  errorResponse,
  stubBackend,
  type BackendMock,
  type StubbedRoute,
} from '../test/stubBackend';
import { TemplatesPage } from './TemplatesPage';

const chips: TemplateSummary = {
  id: '5d0c2a8e-1f3b-4c7a-9e21-3a4b5c6d7e01',
  name: 'Chips',
  tags: [],
  tile_count: 12,
  updated_at: '2026-10-05T12:00:00Z',
  moderation: 'none',
  moderation_reason: null,
  visibility: 'private',
  first_made_public_at: null,
  removed_images: [],
};
const sodas: TemplateSummary = {
  id: '5d0c2a8e-1f3b-4c7a-9e21-3a4b5c6d7e02',
  name: 'Sodas',
  tags: [],
  tile_count: 1,
  updated_at: '2026-10-04T12:00:00Z',
  moderation: 'none',
  moderation_reason: null,
  visibility: 'private',
  first_made_public_at: null,
  removed_images: [],
};

const createdTemplate: Template = {
  id: '5d0c2a8e-1f3b-4c7a-9e21-3a4b5c6d7e03',
  name: 'Fromages',
  tags: [],
  created_at: '2026-10-06T12:00:00Z',
  updated_at: '2026-10-06T12:00:00Z',
  tiers: [],
  tiles: [],
  max_tiles: 32,
  moderation: 'none',
  moderation_reason: null,
  visibility: 'private',
  first_made_public_at: null,
};

function renderTemplatesPage() {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={['/templates']}>
      <Routes>
        <Route path="/templates" element={<TemplatesPage />} />
        <Route path="/templates/:templateId" element={<h1>Éditeur</h1>} />
        <Route path="/r/:code" element={<h1>Lobby</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

function listOf(templates: TemplateSummary[]): () => Response {
  return () => Response.json({ items: templates });
}

function stubTemplatesBackend(routes: Record<string, StubbedRoute>): BackendMock {
  return stubBackend({ 'GET /templates/removed': () => Response.json({ items: [] }), ...routes });
}

function calledRoutesExceptRemovedList(fetchMock: BackendMock): string[] {
  return calledRoutes(fetchMock).filter((route) => route !== 'GET /templates/removed');
}

describe('TemplatesPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('lists the templates with their tile count and last change date', async () => {
    stubTemplatesBackend({ 'GET /templates': listOf([chips, sodas]) });

    renderTemplatesPage();

    expect(screen.getByRole('status')).toBeInTheDocument();
    const items: HTMLElement[] = await screen.findAllByRole('listitem');
    expect(items).toHaveLength(2);
    expect(within(items[0]).getByRole('link', { name: 'Chips' })).toHaveAttribute(
      'href',
      `/templates/${chips.id}`,
    );
    expect(items[0]).toHaveTextContent('12 tuiles');
    expect(items[0]).toHaveTextContent('Modifié le 5 octobre 2026');
    expect(items[1]).toHaveTextContent('1 tuile');
  });

  it('shows the reason why a template was hidden', async () => {
    stubTemplatesBackend({
      'GET /templates': listOf([
        { ...chips, moderation: 'hidden', moderation_reason: 'Harcèlement' },
      ]),
    });

    renderTemplatesPage();

    const hidden: HTMLElement = await screen.findByRole('listitem');
    expect(hidden).toHaveTextContent('Motif : Harcèlement');
  });

  it('says which images of a template were removed, the decision and its reason', async () => {
    stubTemplatesBackend({
      'GET /templates': listOf([
        {
          ...chips,
          removed_images: [
            {
              tile_id: 'tile-paprika',
              tile_text: 'Paprika',
              tile_position: 0,
              status: 'hidden',
              reason: 'Violence',
            },
            {
              tile_id: 'tile-image',
              tile_text: null,
              tile_position: 2,
              status: 'deleted',
              reason: 'Contenu illicite',
            },
          ],
        },
      ]),
    });

    renderTemplatesPage();

    const [paprika, imageOnly] = await screen.findAllByRole('listitem').then((items) => {
      return items.filter((item) => item.tagName === 'LI' && item.querySelector('ul') === null);
    });
    expect(paprika).toHaveTextContent('Paprika');
    expect(paprika).toHaveTextContent('Image masquée par la modération');
    expect(paprika).toHaveTextContent('Motif : Violence');
    expect(imageOnly).toHaveTextContent('Tuile 3');
    expect(imageOnly).toHaveTextContent('Image supprimée par la modération');
    expect(imageOnly).toHaveTextContent('Motif : Contenu illicite');
  });

  it('lists the templates deleted by the moderation with their reason', async () => {
    stubTemplatesBackend({
      'GET /templates': listOf([]),
      'GET /templates/removed': () =>
        Response.json({
          items: [
            {
              id: 'removed-template',
              name: 'Vieux modèle',
              removed_at: '2026-10-07T12:00:00Z',
              reason: 'Contenu illicite',
            },
          ],
        }),
    });

    renderTemplatesPage();

    const section: HTMLElement = (
      await screen.findByRole('heading', { name: 'Supprimés par la modération' })
    ).closest('section') as HTMLElement;
    expect(section).toHaveTextContent('Vieux modèle');
    expect(section).toHaveTextContent('Supprimé le 7 octobre 2026');
    expect(section).toHaveTextContent('Motif : Contenu illicite');
    expect(within(section).queryByRole('link')).not.toBeInTheDocument();
  });

  it('hides the section of the deleted templates when there are none', async () => {
    const backend: BackendMock = stubTemplatesBackend({
      'GET /templates': listOf([chips]),
      'GET /templates/removed': () => Response.json({ items: [] }),
    });

    renderTemplatesPage();

    await screen.findByRole('listitem');
    await waitFor(() => expect(calledRoutes(backend)).toContain('GET /templates/removed'));
    expect(screen.queryByText('Supprimés par la modération')).not.toBeInTheDocument();
  });

  it('shows an error when the deleted templates cannot be read', async () => {
    stubTemplatesBackend({
      'GET /templates': listOf([chips]),
      'GET /templates/removed': () => errorResponse(500, 'internal_error'),
    });

    renderTemplatesPage();

    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });

  it('marks a template hidden by the moderation instead of offering a room', async () => {
    stubTemplatesBackend({
      'GET /templates': listOf([
        { ...chips, moderation: 'hidden', moderation_reason: 'Harcèlement' },
        sodas,
      ]),
    });

    renderTemplatesPage();

    const [hidden, visible] = await screen.findAllByRole('listitem');
    expect(within(hidden).getByText('Masqué')).toBeInTheDocument();
    expect(
      within(hidden).queryByRole('button', { name: /Créer une salle/ }),
    ).not.toBeInTheDocument();
    expect(within(visible).queryByText('Masqué')).not.toBeInTheDocument();
    expect(
      within(visible).getByRole('button', { name: 'Créer une salle avec Sodas' }),
    ).toBeVisible();
  });

  it('marks the public templates', async () => {
    stubTemplatesBackend({
      'GET /templates': listOf([
        { ...chips, visibility: 'public', first_made_public_at: '2026-10-31T10:00:00Z' },
        sodas,
      ]),
    });

    renderTemplatesPage();

    const [publicTemplate, privateTemplate] = await screen.findAllByRole('listitem');
    expect(within(publicTemplate).getByText('Public')).toBeInTheDocument();
    expect(
      within(publicTemplate).getByRole('button', { name: 'Créer une salle avec Chips' }),
    ).toBeVisible();
    expect(within(privateTemplate).queryByText('Public')).not.toBeInTheDocument();
  });

  it('invites to create a template when there is none', async () => {
    stubTemplatesBackend({ 'GET /templates': listOf([]) });

    renderTemplatesPage();

    expect(await screen.findByText(/aucun modèle/)).toBeInTheDocument();
    expect(screen.queryByRole('list')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Nouveau modèle' })).toBeInTheDocument();
  });

  it('shows an error when the list cannot be loaded', async () => {
    const consoleError: MockInstance<typeof console.error> = vi
      .spyOn(console, 'error')
      .mockImplementation(() => {});
    stubTemplatesBackend({ 'GET /templates': () => errorResponse(500, 'internal_error') });

    renderTemplatesPage();

    expect(await screen.findByRole('alert')).toHaveTextContent('Erreur interne du serveur');
    consoleError.mockRestore();
  });

  it('creates a template and opens it in the editor', async () => {
    const fetchMock: BackendMock = stubTemplatesBackend({
      'GET /templates': listOf([]),
      'POST /templates': () => Response.json(createdTemplate, { status: 201 }),
    });
    renderTemplatesPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Nouveau modèle' }));
    const dialog: HTMLElement = screen.getByRole('dialog', { name: 'Nouveau modèle' });
    fireEvent.change(within(dialog).getByLabelText('Nom'), { target: { value: 'Fromages' } });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Créer' }));

    expect(await screen.findByRole('heading', { name: 'Éditeur' })).toBeInTheDocument();
    const createCall: [request: Request] | undefined = fetchMock.mock.calls.find(
      ([request]) => request.method === 'POST',
    );
    await expect(createCall?.[0].json()).resolves.toEqual({ name: 'Fromages' });
  });

  it('stays on the list when the creation is cancelled before its answer', async () => {
    let answerCreation: ((response: Response) => void) | undefined;
    stubTemplatesBackend({
      'GET /templates': listOf([]),
      'POST /templates': () =>
        new Promise<Response>((resolve) => {
          answerCreation = resolve;
        }),
    });
    renderTemplatesPage();
    fireEvent.click(await screen.findByRole('button', { name: 'Nouveau modèle' }));
    const dialog: HTMLElement = screen.getByRole('dialog', { name: 'Nouveau modèle' });
    fireEvent.change(within(dialog).getByLabelText('Nom'), { target: { value: 'Fromages' } });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Créer' }));
    await waitFor(() => expect(answerCreation).toBeDefined());

    fireEvent.click(within(dialog).getByRole('button', { name: 'Annuler' }));
    await act(async () => {
      answerCreation?.(Response.json(createdTemplate, { status: 201 }));
      await new Promise((resolve) => setTimeout(resolve, 20));
    });

    expect(screen.queryByRole('heading', { name: 'Éditeur' })).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Mes modèles' })).toBeInTheDocument();
  });

  it('shows the field error when the name is blank', async () => {
    stubTemplatesBackend({
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

    fireEvent.click(await screen.findByRole('button', { name: 'Nouveau modèle' }));
    const dialog: HTMLElement = screen.getByRole('dialog', { name: 'Nouveau modèle' });
    fireEvent.change(within(dialog).getByLabelText('Nom'), { target: { value: '   ' } });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Créer' }));

    expect(await within(dialog).findByText('Au moins 1 caractère.')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('Nom')).toHaveAttribute('aria-invalid', 'true');
    expect(dialog).toBeVisible();
    expect(screen.queryByRole('heading', { name: 'Éditeur' })).not.toBeInTheDocument();
  });

  it('deletes a template after confirmation and refreshes the list', async () => {
    let templates: TemplateSummary[] = [chips, sodas];
    const fetchMock: BackendMock = stubTemplatesBackend({
      'GET /templates': () => Response.json({ items: templates }),
      [`DELETE /templates/${chips.id}`]: () => {
        templates = [sodas];
        return new Response(null, { status: 204 });
      },
    });
    renderTemplatesPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Supprimer Chips' }));
    const dialog: HTMLElement = screen.getByRole('dialog', { name: 'Supprimer « Chips » ?' });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Supprimer' }));

    await waitFor(() => expect(screen.queryByText('Chips')).not.toBeInTheDocument());
    expect(screen.getByText('Sodas')).toBeInTheDocument();
    expect(calledRoutesExceptRemovedList(fetchMock)).toEqual([
      'GET /templates',
      `DELETE /templates/${chips.id}`,
      'GET /templates',
    ]);
  });

  it('keeps the template when the deletion is cancelled', async () => {
    const fetchMock: BackendMock = stubTemplatesBackend({ 'GET /templates': listOf([chips]) });
    renderTemplatesPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Supprimer Chips' }));
    const dialog: HTMLElement = screen.getByRole('dialog', { name: 'Supprimer « Chips » ?' });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Annuler' }));

    expect(dialog).not.toBeVisible();
    expect(screen.getByText('Chips')).toBeInTheDocument();
    expect(calledRoutesExceptRemovedList(fetchMock)).toEqual(['GET /templates']);
  });

  it('shows an error when the template to delete no longer exists', async () => {
    stubTemplatesBackend({
      'GET /templates': listOf([chips]),
      [`DELETE /templates/${chips.id}`]: () => errorResponse(404, 'template_not_found'),
    });
    renderTemplatesPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Supprimer Chips' }));
    const dialog: HTMLElement = screen.getByRole('dialog', { name: 'Supprimer « Chips » ?' });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Supprimer' }));

    expect(await within(dialog).findByRole('alert')).toHaveTextContent(
      'Ce modèle est introuvable.',
    );
  });

  describe('create a room', () => {
    it('creates a room from a template and opens its lobby', async () => {
      const fetchMock: BackendMock = stubTemplatesBackend({
        'GET /templates': listOf([chips]),
        'POST /rooms': () => Response.json(aliceRoom, { status: 201 }),
      });
      renderTemplatesPage();

      fireEvent.click(await screen.findByRole('button', { name: 'Créer une salle avec Chips' }));

      expect(await screen.findByRole('heading', { name: 'Lobby' })).toBeInTheDocument();
      const post = fetchMock.mock.calls.find(([request]) => request.method === 'POST');
      expect(await post?.[0].json()).toEqual({ template_id: chips.id });
    });

    it('says why a template without tiles cannot be played', async () => {
      stubTemplatesBackend({
        'GET /templates': listOf([chips]),
        'POST /rooms': () => errorResponse(409, 'template_has_no_tiles'),
      });
      renderTemplatesPage();

      fireEvent.click(await screen.findByRole('button', { name: 'Créer une salle avec Chips' }));

      expect(await screen.findByRole('alert')).toHaveTextContent(
        'Ajoutez au moins une tuile à ce modèle pour jouer avec.',
      );
      expect(screen.queryByRole('heading', { name: 'Lobby' })).not.toBeInTheDocument();
    });
  });
});
