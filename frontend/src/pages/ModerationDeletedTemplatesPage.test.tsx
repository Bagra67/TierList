import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { DeletedTemplate } from '../api/moderation';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { calledRoutes, stubBackend, type BackendMock } from '../test/stubBackend';
import { ModerationDeletedTemplatesPage } from './ModerationDeletedTemplatesPage';

const NOW: Date = new Date('2026-11-19T12:00:00Z');

function deletedTemplate(overrides: Partial<DeletedTemplate>): DeletedTemplate {
  return {
    id: 'spices-id',
    name: 'Épices du monde',
    owner_id: 'camille-id',
    owner_name: 'Camille',
    tile_count: 12,
    moderation: 'none',
    deleted_at: '2026-11-18T10:00:00Z',
    erase_at: '2026-12-18T10:00:00Z',
    deletion_reason: null,
    ...overrides,
  };
}

const spices: DeletedTemplate = deletedTemplate({});
const insults: DeletedTemplate = deletedTemplate({
  id: 'insults-id',
  name: 'Insultes en vrac',
  owner_id: 'bob-id',
  owner_name: 'Bob',
  tile_count: 1,
  deleted_at: '2026-10-21T10:00:00Z',
  erase_at: '2026-11-20T10:00:00Z',
  deletion_reason: 'Contenu haineux',
});

function renderPage(routes: Parameters<typeof stubBackend>[0]): BackendMock {
  const fetchMock: BackendMock = stubBackend(routes);
  renderWithQueryClient(
    <MemoryRouter>
      <ModerationDeletedTemplatesPage />
    </MemoryRouter>,
  );
  return fetchMock;
}

function lastSearch(fetchMock: BackendMock): URLSearchParams {
  const requests: Request[] = fetchMock.mock.calls
    .map(([request]) => request)
    .filter((request) => request.url.includes('/moderation/templates/deleted'));
  return new URL(requests.at(-1)?.url ?? '').searchParams;
}

describe('ModerationDeletedTemplatesPage', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(NOW);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('lists the deleted templates with their owner, deletion and countdown', async () => {
    renderPage({
      'GET /moderation/templates/deleted': () =>
        Response.json({ templates: [insults, spices], has_more: false }),
    });

    const rows: HTMLElement[] = await screen.findAllByRole('listitem');
    expect(within(rows[0]).getByRole('link', { name: 'Insultes en vrac' })).toHaveAttribute(
      'href',
      '/moderation/templates/insults-id',
    );
    expect(within(rows[0]).getByRole('link', { name: 'Bob' })).toHaveAttribute(
      'href',
      '/moderation/accounts/bob-id',
    );
    expect(within(rows[0]).getByText('Par la modération')).toBeInTheDocument();
    expect(within(rows[0]).getByText('« Contenu haineux »')).toBeInTheDocument();
    expect(within(rows[0]).getByText('Effacé dans 1 jour')).toBeInTheDocument();
    expect(within(rows[1]).getByText(/Supprimé par son auteur le/)).toBeInTheDocument();
    expect(within(rows[1]).getByText('Effacé dans 29 jours')).toBeInTheDocument();
    expect(within(rows[1]).queryByText('Par la modération')).not.toBeInTheDocument();
  });

  it('sends the owner and name filters on search, and the dates as soon as they change', async () => {
    const fetchMock: BackendMock = renderPage({
      'GET /moderation/templates/deleted': () => Response.json({ templates: [], has_more: false }),
    });

    fireEvent.change(await screen.findByLabelText('Propriétaire'), {
      target: { value: '  camille ' },
    });
    fireEvent.change(screen.getByLabelText('Nom du modèle'), { target: { value: 'épices' } });
    fireEvent.click(screen.getByRole('button', { name: 'Rechercher' }));
    await waitFor(() => expect(lastSearch(fetchMock).get('owner')).toBe('camille'));
    expect(lastSearch(fetchMock).get('name')).toBe('épices');

    fireEvent.change(screen.getByLabelText('Du'), { target: { value: '2026-11-01' } });
    await waitFor(() => expect(lastSearch(fetchMock).get('deleted_after')).not.toBeNull());
    expect(
      await screen.findByText('Aucun modèle supprimé ne correspond à ces filtres.'),
    ).toBeInTheDocument();
  });

  it('says when there is no deleted template', async () => {
    renderPage({
      'GET /moderation/templates/deleted': () => Response.json({ templates: [], has_more: false }),
    });

    expect(await screen.findByText('Aucun modèle supprimé.')).toBeInTheDocument();
  });

  it.each([
    ['Restaurer', 'Restaurer « Épices du monde » ?', 'restore'],
    ['Supprimer définitivement', 'Supprimer définitivement « Épices du monde » ?', 'purge'],
  ])('%s a template with a reason', async (button, dialogName, action) => {
    const fetchMock: BackendMock = renderPage({
      'GET /moderation/templates/deleted': () =>
        Response.json({ templates: [spices], has_more: false }),
      [`POST /moderation/templates/spices-id/${action}`]: () => new Response(null, { status: 204 }),
    });

    fireEvent.click(await screen.findByRole('button', { name: button }));
    const dialog: HTMLElement = screen.getByRole('dialog', { name: dialogName });
    fireEvent.change(within(dialog).getByLabelText('Motif'), { target: { value: 'Erreur' } });
    fireEvent.click(within(dialog).getByRole('button', { name: button }));

    await waitFor(() =>
      expect(calledRoutes(fetchMock)).toContain(`POST /moderation/templates/spices-id/${action}`),
    );
    await waitFor(() => expect(dialog).not.toBeVisible());
  });
});
