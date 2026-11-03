import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { HiddenGame, ReportedContent } from '../api/moderation';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { errorResponse, stubBackend, type BackendMock } from '../test/stubBackend';
import { ModerationReportsPage } from './ModerationReportsPage';

const reportedImage: ReportedContent = {
  target_type: 'image',
  target_id: 'image-id',
  label: null,
  owner_id: 'camille-id',
  owner_name: 'Camille',
  report_count: 2,
  reasons: [{ reason: 'sexual', count: 2 }],
  details: ['Une photo choquante'],
  first_reported_at: '2026-10-20T12:00:00Z',
  image_url: 'https://images.example.com/tile.webp',
  public_token: null,
};

const reportedGuest: ReportedContent = {
  target_type: 'nickname',
  target_id: 'lou-id',
  label: 'xX_spam_Xx',
  owner_id: null,
  owner_name: null,
  report_count: 1,
  reasons: [{ reason: 'spam', count: 1 }],
  details: [],
  first_reported_at: '2026-10-21T12:00:00Z',
  image_url: null,
  public_token: null,
};

const reportedGame: ReportedContent = {
  target_type: 'game',
  target_id: 'game-id',
  label: 'Épices',
  owner_id: 'max-id',
  owner_name: 'Max',
  report_count: 1,
  reasons: [{ reason: 'harassment', count: 1 }],
  details: [],
  first_reported_at: '2026-10-22T12:00:00Z',
  image_url: null,
  public_token: 'results-token',
};

const hiddenGame: HiddenGame = {
  id: 'hidden-game-id',
  template_name: 'Fromages',
  hidden_at: '2026-10-23T12:00:00Z',
};

const noContent: Response = Response.json({ contents: [], has_more: false });
const noGame: Response = Response.json({ games: [], has_more: false });

function renderPage(routes: Parameters<typeof stubBackend>[0]): BackendMock {
  const fetchMock: BackendMock = stubBackend({
    'GET /moderation/reports': () => noContent.clone(),
    'GET /moderation/games/hidden': () => noGame.clone(),
    ...routes,
  });
  renderWithQueryClient(
    <MemoryRouter>
      <ModerationReportsPage />
    </MemoryRouter>,
  );
  return fetchMock;
}

function queueWith(...contents: ReportedContent[]): () => Response {
  return () => Response.json({ contents, has_more: false });
}

async function sentBody(fetchMock: BackendMock, path: string): Promise<unknown> {
  const request: Request = await waitFor(() => {
    const call = fetchMock.mock.calls.find(
      ([sent]) => sent.method === 'POST' && new URL(sent.url).pathname.endsWith(path),
    );
    if (call === undefined) throw new Error(`No POST ${path} yet`);
    return call[0];
  });
  return request.clone().json();
}

async function decide(buttonName: string, dialogName: string, submitName: string) {
  fireEvent.click(await screen.findByRole('button', { name: buttonName }));
  const dialog: HTMLElement = screen.getByRole('dialog', { name: dialogName });
  fireEvent.change(within(dialog).getByLabelText('Motif'), { target: { value: 'Illicite' } });
  fireEvent.click(within(dialog).getByRole('button', { name: submitName }));
  return dialog;
}

describe('ModerationReportsPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('shows a reported image with its owner, its number, its reasons and its details', async () => {
    renderPage({ 'GET /moderation/reports': queueWith(reportedImage) });

    expect(await screen.findByRole('img', { name: 'Image' })).toHaveAttribute(
      'src',
      reportedImage.image_url,
    );
    expect(screen.getByText(/Camille · 2 signalements/)).toBeInTheDocument();
    expect(screen.getByText('Contenu sexuel ×2')).toBeInTheDocument();
    expect(screen.getByText('Une photo choquante')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Voir le compte' })).toHaveAttribute(
      'href',
      '/moderation/accounts/camille-id',
    );
  });

  it('shows a guest without any account to open', async () => {
    renderPage({ 'GET /moderation/reports': queueWith(reportedGuest) });

    expect(await screen.findByText('xX_spam_Xx')).toBeInTheDocument();
    expect(screen.getByText(/Invité · 1 signalement/)).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Voir le compte' })).not.toBeInTheDocument();
  });

  it('links a reported game to its results', async () => {
    renderPage({ 'GET /moderation/reports': queueWith(reportedGame) });

    expect(await screen.findByRole('link', { name: 'Voir les résultats' })).toHaveAttribute(
      'href',
      '/results/results-token',
    );
  });

  it('says when nothing is reported, and shows no hidden games section', async () => {
    renderPage({});

    expect(await screen.findByText('Aucun signalement ouvert.')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Parties masquées' })).not.toBeInTheDocument();
  });

  it('shows why the queue cannot be read', async () => {
    renderPage({ 'GET /moderation/reports': () => errorResponse(403, 'super_admin_required') });

    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });

  it('offers the decisions that fit each content', async () => {
    renderPage({
      'GET /moderation/reports': queueWith(reportedImage, reportedGuest, reportedGame),
    });

    await screen.findByText('xX_spam_Xx');
    const names: string[] = screen
      .getAllByRole('button')
      .map((button: HTMLElement) => button.getAttribute('aria-label') ?? '');
    expect(names).toEqual([
      'Classer sans suite : Image',
      'Masquer : Image',
      'Supprimer : Image',
      'Classer sans suite : xX_spam_Xx',
      'Retirer le pseudo : xX_spam_Xx',
      'Classer sans suite : Épices',
      'Masquer : Épices',
    ]);
  });

  it('dismisses a content with a reason, then reads the queue again', async () => {
    let reads: number = 0;
    const fetchMock: BackendMock = renderPage({
      'GET /moderation/reports': () => {
        reads += 1;
        return reads === 1 ? queueWith(reportedGame)() : noContent.clone();
      },
      'POST /moderation/reports/dismiss': () => new Response(null, { status: 204 }),
    });

    await decide('Classer sans suite : Épices', 'Classer sans suite ?', 'Classer sans suite');

    await expect(sentBody(fetchMock, '/moderation/reports/dismiss')).resolves.toEqual({
      target_type: 'game',
      target_id: 'game-id',
      reason: 'Illicite',
    });
    expect(await screen.findByText('Aucun signalement ouvert.')).toBeInTheDocument();
  });

  it('hides and deletes an image through its routes', async () => {
    const fetchMock: BackendMock = renderPage({
      'GET /moderation/reports': queueWith(reportedImage),
      'POST /moderation/images/image-id/hide': () => new Response(null, { status: 204 }),
      'POST /moderation/images/image-id/delete': () => new Response(null, { status: 204 }),
    });

    await decide('Masquer : Image', 'Masquer cette image ?', 'Masquer');
    await expect(sentBody(fetchMock, '/moderation/images/image-id/hide')).resolves.toEqual({
      reason: 'Illicite',
    });

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    await decide('Supprimer : Image', 'Supprimer cette image ?', 'Supprimer');
    await expect(sentBody(fetchMock, '/moderation/images/image-id/delete')).resolves.toEqual({
      reason: 'Illicite',
    });
  });

  it('removes a nickname with the target of its report', async () => {
    const fetchMock: BackendMock = renderPage({
      'GET /moderation/reports': queueWith(reportedGuest),
      'POST /moderation/nicknames/remove': () => new Response(null, { status: 204 }),
    });

    await decide('Retirer le pseudo : xX_spam_Xx', 'Retirer ce pseudo ?', 'Retirer le pseudo');

    await expect(sentBody(fetchMock, '/moderation/nicknames/remove')).resolves.toEqual({
      target_id: 'lou-id',
      reason: 'Illicite',
    });
  });

  it('hides a game', async () => {
    const fetchMock: BackendMock = renderPage({
      'GET /moderation/reports': queueWith(reportedGame),
      'POST /moderation/games/game-id/hide': () => new Response(null, { status: 204 }),
    });

    await decide('Masquer : Épices', 'Masquer cette partie ?', 'Masquer');

    await expect(sentBody(fetchMock, '/moderation/games/game-id/hide')).resolves.toEqual({
      reason: 'Illicite',
    });
  });

  it('shows a refused decision and keeps the dialog open', async () => {
    renderPage({
      'GET /moderation/reports': queueWith(reportedGame),
      'POST /moderation/reports/dismiss': () => errorResponse(404, 'reports_not_open'),
    });

    const dialog: HTMLElement = await decide(
      'Classer sans suite : Épices',
      'Classer sans suite ?',
      'Classer sans suite',
    );

    expect(await within(dialog).findByRole('alert')).toHaveTextContent(
      "Ce contenu n'a plus de signalement ouvert",
    );
    expect(screen.getByRole('dialog', { name: 'Classer sans suite ?' })).toBeInTheDocument();
  });

  it('lists the hidden games and shows one again with a reason', async () => {
    const fetchMock: BackendMock = renderPage({
      'GET /moderation/games/hidden': () => Response.json({ games: [hiddenGame], has_more: false }),
      'POST /moderation/games/hidden-game-id/unhide': () => new Response(null, { status: 204 }),
    });

    expect(await screen.findByRole('heading', { name: 'Parties masquées' })).toBeInTheDocument();
    await decide('Réafficher : Fromages', 'Réafficher cette partie ?', 'Réafficher');

    await expect(sentBody(fetchMock, '/moderation/games/hidden-game-id/unhide')).resolves.toEqual({
      reason: 'Illicite',
    });
  });
});
