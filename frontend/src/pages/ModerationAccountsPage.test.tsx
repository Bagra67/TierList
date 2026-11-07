import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { AccountSearchPage, AccountSummary } from '../api/moderation';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { stubBackend } from '../test/stubBackend';
import { ModerationAccountsPage } from './ModerationAccountsPage';

function account(overrides: Partial<AccountSummary>): AccountSummary {
  return {
    id: 'max-id',
    display_name: 'Max',
    email: 'max@example.com',
    created_at: '2026-10-01T12:00:00Z',
    role: 'user',
    banned: false,
    ...overrides,
  };
}

function stubSearch(pages: Record<string, AccountSearchPage>): URLSearchParams[] {
  const queries: URLSearchParams[] = [];
  stubBackend({
    'GET /moderation/accounts': (request: Request) => {
      const query: URLSearchParams = new URL(request.url).searchParams;
      queries.push(query);
      return Response.json(pages[query.get('offset') ?? ''] ?? { accounts: [], has_more: false });
    },
  });
  return queries;
}

function renderAccountsPage() {
  return renderWithQueryClient(
    <MemoryRouter>
      <ModerationAccountsPage />
    </MemoryRouter>,
  );
}

describe('ModerationAccountsPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('lists the accounts with a link to their page and their status', async () => {
    stubSearch({
      '0': {
        accounts: [
          account({ banned: true }),
          account({ id: 'nina-id', display_name: 'Nina', role: 'super_admin' }),
        ],
        has_more: false,
      },
    });
    renderAccountsPage();

    const [max, nina] = await screen.findAllByRole('listitem');
    expect(within(max).getByRole('link', { name: 'Max' })).toHaveAttribute(
      'href',
      '/moderation/accounts/max-id',
    );
    expect(max).toHaveTextContent('max@example.com');
    expect(within(max).getByText('Banni')).toBeInTheDocument();
    expect(within(nina).getByText('Super admin')).toBeInTheDocument();
    expect(within(nina).queryByText('Banni')).not.toBeInTheDocument();
  });

  it('searches the text when the form is sent', async () => {
    const queries: URLSearchParams[] = stubSearch({});
    renderAccountsPage();
    await screen.findByText('Aucun compte ne correspond.');

    fireEvent.change(screen.getByLabelText('Nom ou e-mail'), { target: { value: ' max@ ' } });
    fireEvent.click(screen.getByRole('button', { name: 'Rechercher' }));

    await waitFor(() => expect(queries.at(-1)?.get('query')).toBe('max@'));
    expect(queries[0].get('query')).toBeNull();
  });

  it('loads the next page on demand', async () => {
    const queries: URLSearchParams[] = stubSearch({
      '0': { accounts: [account({})], has_more: true },
      '1': { accounts: [account({ id: 'lou-id', display_name: 'Lou' })], has_more: false },
    });
    renderAccountsPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Voir plus' }));

    expect(await screen.findByRole('link', { name: 'Lou' })).toBeVisible();
    expect(queries.map((query) => query.get('offset'))).toEqual(['0', '1']);
  });
});
