import { fireEvent, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { ModerationLogEntry, ModerationLogPage as LogPage } from '../api/moderation';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { errorResponse, stubBackend } from '../test/stubBackend';
import { ModerationLogPage } from './ModerationLogPage';

function renderLogPage() {
  return renderWithQueryClient(
    <MemoryRouter>
      <ModerationLogPage />
    </MemoryRouter>,
  );
}

function entry(overrides: Partial<ModerationLogEntry>): ModerationLogEntry {
  return {
    id: 'entry-1',
    created_at: '2026-10-31T18:42:00Z',
    actor_id: 'nina-id',
    actor_name: 'Nina',
    action: 'hide',
    target_type: 'template',
    target_id: null,
    target_label: 'Top 10',
    reason: 'Harcèlement',
    ...overrides,
  };
}

const superAdmins = [
  { id: 'nina-id', display_name: 'Nina' },
  { id: 'sam-id', display_name: 'Samuel' },
];

function stubLog(pages: Record<string, LogPage>): URLSearchParams[] {
  const queries: URLSearchParams[] = [];
  stubBackend({
    'GET /moderation/super-admins': () => Response.json(superAdmins),
    'GET /moderation/log': (request: Request) => {
      const query: URLSearchParams = new URL(request.url).searchParams;
      queries.push(query);
      return Response.json(pages[query.get('offset') ?? ''] ?? { entries: [], has_more: false });
    },
  });
  return queries;
}

describe('ModerationLogPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('shows who did what, on what, when and why', async () => {
    stubLog({ '0': { entries: [entry({})], has_more: false } });
    renderLogPage();

    const row = (await screen.findByRole('cell', { name: 'Nina' })).closest('tr');
    expect(row).not.toBeNull();
    const cells = within(row as HTMLElement).getAllByRole('cell');
    expect(cells.map((cell) => cell.textContent)).toEqual([
      expect.stringContaining('2026'),
      'Nina',
      'Masquer',
      'Modèle « Top 10 »',
      'Harcèlement',
    ]);
    expect(screen.getByRole('heading', { name: 'Journal de modération' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Voir plus' })).not.toBeInTheDocument();
  });

  it('links an account target to its page', async () => {
    stubLog({
      '0': {
        entries: [
          entry({
            target_type: 'account',
            target_id: 'max-id',
            target_label: 'Max',
            action: 'ban',
          }),
        ],
        has_more: false,
      },
    });
    renderLogPage();

    expect(await screen.findByRole('link', { name: 'Compte « Max »' })).toHaveAttribute(
      'href',
      '/moderation/accounts/max-id',
    );
  });

  it('says when the log is empty', async () => {
    stubLog({});
    renderLogPage();

    expect(
      await screen.findByText("Aucune action de modération pour l'instant."),
    ).toBeInTheDocument();
  });

  it('loads the next page with see more', async () => {
    const queries = stubLog({
      '0': { entries: [entry({ id: 'a', target_label: 'Premier' })], has_more: true },
      '1': { entries: [entry({ id: 'b', target_label: 'Second' })], has_more: false },
    });
    renderLogPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Voir plus' }));

    expect(await screen.findByText('Modèle « Second »')).toBeInTheDocument();
    expect(screen.getByText('Modèle « Premier »')).toBeInTheDocument();
    expect(queries.map((query) => query.get('offset'))).toEqual(['0', '1']);
  });

  it('filters by target when the search is sent', async () => {
    const queries = stubLog({});
    renderLogPage();
    await screen.findByText("Aucune action de modération pour l'instant.");

    fireEvent.change(screen.getByLabelText('Cible'), { target: { value: '  Top 10 ' } });
    fireEvent.click(screen.getByRole('button', { name: 'Rechercher' }));

    expect(
      await screen.findByText('Aucune action ne correspond à ces filtres.'),
    ).toBeInTheDocument();
    expect(queries.at(-1)?.get('target')).toBe('Top 10');
  });

  it('filters by super admin', async () => {
    const queries = stubLog({});
    renderLogPage();
    const select = screen.getByLabelText('Super admin');
    await screen.findByRole('option', { name: 'Samuel' });

    fireEvent.change(select, { target: { value: 'sam-id' } });

    expect(
      await screen.findByText('Aucune action ne correspond à ces filtres.'),
    ).toBeInTheDocument();
    expect(queries.at(-1)?.get('actor_id')).toBe('sam-id');
  });

  it('says why the super admins cannot be listed in the filter', async () => {
    stubBackend({
      'GET /moderation/super-admins': () => errorResponse(403, 'super_admin_required'),
      'GET /moderation/log': () => Response.json({ entries: [], has_more: false }),
    });
    renderLogPage();

    expect(await screen.findByText('Seul un super admin peut faire cela.')).toBeInTheDocument();
  });

  it('shows the translated error when the log cannot be read', async () => {
    stubBackend({
      'GET /moderation/super-admins': () => Response.json(superAdmins),
      'GET /moderation/log': () => errorResponse(403, 'super_admin_required'),
    });
    renderLogPage();

    expect(await screen.findByText('Seul un super admin peut faire cela.')).toBeInTheDocument();
  });
});
