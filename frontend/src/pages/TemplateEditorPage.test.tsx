import { fireEvent, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, type MockInstance, vi } from 'vitest';

import type { Template, Tier, Tile } from '../api/templates';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { calledRoutes, errorResponse, stubBackend } from '../test/stubBackend';
import { TemplateEditorPage } from './TemplateEditorPage';

type BackendMock = ReturnType<typeof stubBackend>;

const templateId: string = '5d0c2a8e-1f3b-4c7a-9e21-3a4b5c6d7e01';
const templateUrl: string = `/templates/${templateId}`;

function makeTier(name: string, position: number, color = '#FF7F7F'): Tier {
  return { id: `tier-${name}`, name, color, position };
}

function makeTile(text: string, position: number): Tile {
  return { id: `tile-${text}`, text, position };
}

function makeTemplate(tiers: Tier[], name = 'Chips', tiles: Tile[] = []): Template {
  return {
    id: templateId,
    name,
    created_at: '2026-10-05T12:00:00Z',
    updated_at: '2026-10-05T12:00:00Z',
    tiers: tiers.map((tier, position) => ({ ...tier, position })),
    tiles: tiles.map((tile, position) => ({ ...tile, position })),
    max_tiles: 32,
  };
}

const [tierS, tierA, tierB]: Tier[] = [makeTier('S', 0), makeTier('A', 1), makeTier('B', 2)];
const chips: Template = makeTemplate([tierS, tierA, tierB]);

function renderEditor() {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={[templateUrl]}>
      <Routes>
        <Route path="/templates/:templateId" element={<TemplateEditorPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

const [pizza, sushi]: Tile[] = [makeTile('Pizza', 0), makeTile('Sushi', 1)];
function withTiles(tiles: Tile[]): Template {
  return makeTemplate([tierS, tierA, tierB], 'Chips', tiles);
}

// Textes des tuiles dans l'ordre affiché (un champ de texte par tuile)
function displayedTileTexts(): string[] {
  return screen
    .queryAllByRole('textbox', { name: /^Texte de la tuile/ })
    .map((input) => (input as HTMLInputElement).value);
}

// Noms des tiers dans l'ordre affiché (un champ de nom par ligne)
function displayedTierNames(): string[] {
  return screen
    .getAllByRole('textbox', { name: /^Nom du tier/ })
    .map((input) => (input as HTMLInputElement).value);
}

async function requestBody(fetchMock: BackendMock, method: string): Promise<unknown> {
  const call: [request: Request] | undefined = fetchMock.mock.calls.find(
    ([request]) => request.method === method,
  );
  return call?.[0].json();
}

describe('TemplateEditorPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('shows the template name and its tiers in order', async () => {
    stubBackend({ [`GET ${templateUrl}`]: () => Response.json(chips) });

    renderEditor();

    expect(await screen.findByRole('heading', { name: 'Chips' })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Nom du template' })).toHaveValue('Chips');
    expect(displayedTierNames()).toEqual(['S', 'A', 'B']);
    expect(screen.getByRole('link', { name: 'Retour à mes templates' })).toHaveAttribute(
      'href',
      '/templates',
    );
  });

  it('shows an error when the template does not exist', async () => {
    const consoleError: MockInstance<typeof console.error> = vi
      .spyOn(console, 'error')
      .mockImplementation(() => {});
    stubBackend({ [`GET ${templateUrl}`]: () => errorResponse(404, 'template_not_found') });

    renderEditor();

    expect(await screen.findByRole('alert')).toHaveTextContent('Ce template est introuvable.');
    consoleError.mockRestore();
  });

  describe('template name', () => {
    it('renames the template when the field is validated', async () => {
      const fetchMock: BackendMock = stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(chips),
        [`PATCH ${templateUrl}`]: () =>
          Response.json(makeTemplate([tierS, tierA, tierB], 'Crisps')),
      });
      renderEditor();
      const nameField: HTMLElement = await screen.findByRole('textbox', {
        name: 'Nom du template',
      });

      fireEvent.change(nameField, { target: { value: 'Crisps' } });
      fireEvent.submit(nameField);

      expect(await screen.findByRole('heading', { name: 'Crisps' })).toBeInTheDocument();
      await expect(requestBody(fetchMock, 'PATCH')).resolves.toEqual({ name: 'Crisps' });
    });

    it('sends nothing when the name did not change', async () => {
      const fetchMock: BackendMock = stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(chips),
      });
      renderEditor();
      const nameField: HTMLElement = await screen.findByRole('textbox', {
        name: 'Nom du template',
      });

      fireEvent.change(nameField, { target: { value: '  Chips ' } });
      fireEvent.blur(nameField);

      expect(calledRoutes(fetchMock)).toEqual([`GET ${templateUrl}`]);
    });

    it('shows the field error when the name is blank', async () => {
      stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(chips),
        [`PATCH ${templateUrl}`]: () =>
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
      renderEditor();
      const nameField: HTMLElement = await screen.findByRole('textbox', {
        name: 'Nom du template',
      });

      fireEvent.change(nameField, { target: { value: '   ' } });
      fireEvent.blur(nameField);

      expect(await screen.findByText('Au moins 1 caractères.')).toBeInTheDocument();
      expect(nameField).toHaveAttribute('aria-invalid', 'true');
    });
  });

  describe('tiers', () => {
    it('renames a tier when the field loses focus', async () => {
      const fetchMock: BackendMock = stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(chips),
        [`PATCH ${templateUrl}/tiers/${tierS.id}`]: () =>
          Response.json(makeTemplate([{ ...tierS, name: 'Top' }, tierA, tierB])),
      });
      renderEditor();
      const firstTierName: HTMLElement = await screen.findByRole('textbox', {
        name: 'Nom du tier 1',
      });

      fireEvent.change(firstTierName, { target: { value: 'Top' } });
      fireEvent.blur(firstTierName);

      await waitFor(() => expect(displayedTierNames()).toEqual(['Top', 'A', 'B']));
      await expect(requestBody(fetchMock, 'PATCH')).resolves.toEqual({ name: 'Top' });
    });

    it('recolors a tier once the color is chosen', async () => {
      const fetchMock: BackendMock = stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(chips),
        [`PATCH ${templateUrl}/tiers/${tierA.id}`]: () =>
          Response.json(makeTemplate([tierS, { ...tierA, color: '#112233' }, tierB])),
      });
      renderEditor();
      const colorField: HTMLElement = await screen.findByLabelText('Couleur du tier A');

      fireEvent.change(colorField, { target: { value: '#112233' } });

      await waitFor(() =>
        expect(calledRoutes(fetchMock)).toContain(`PATCH ${templateUrl}/tiers/${tierA.id}`),
      );
      await expect(requestBody(fetchMock, 'PATCH')).resolves.toEqual({ color: '#112233' });
    });

    it('moves a tier with the move down button', async () => {
      const fetchMock: BackendMock = stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(chips),
        [`PATCH ${templateUrl}/tiers/${tierS.id}`]: () =>
          Response.json(makeTemplate([tierA, tierS, tierB])),
      });
      renderEditor();

      fireEvent.click(await screen.findByRole('button', { name: 'Descendre S' }));

      await waitFor(() => expect(displayedTierNames()).toEqual(['A', 'S', 'B']));
      await expect(requestBody(fetchMock, 'PATCH')).resolves.toEqual({ position: 1 });
    });

    it('cannot move the first tier up nor the last one down', async () => {
      stubBackend({ [`GET ${templateUrl}`]: () => Response.json(chips) });

      renderEditor();

      expect(await screen.findByRole('button', { name: 'Monter S' })).toBeDisabled();
      expect(screen.getByRole('button', { name: 'Descendre B' })).toBeDisabled();
      expect(screen.getByRole('button', { name: 'Monter B' })).toBeEnabled();
    });

    it('adds a tier at the bottom', async () => {
      const fetchMock: BackendMock = stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(chips),
        [`POST ${templateUrl}/tiers`]: () =>
          Response.json(makeTemplate([tierS, tierA, tierB, makeTier('?', 3, '#BFBFBF')]), {
            status: 201,
          }),
      });
      renderEditor();

      fireEvent.click(await screen.findByRole('button', { name: 'Ajouter un tier' }));

      await waitFor(() => expect(displayedTierNames()).toEqual(['S', 'A', 'B', '?']));
      expect(calledRoutes(fetchMock)).toContain(`POST ${templateUrl}/tiers`);
    });

    it('deletes a tier', async () => {
      stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(chips),
        [`DELETE ${templateUrl}/tiers/${tierA.id}`]: () =>
          Response.json(makeTemplate([tierS, tierB])),
      });
      renderEditor();

      fireEvent.click(await screen.findByRole('button', { name: 'Supprimer le tier A' }));

      await waitFor(() => expect(displayedTierNames()).toEqual(['S', 'B']));
    });

    it('cannot delete the only tier left', async () => {
      stubBackend({ [`GET ${templateUrl}`]: () => Response.json(makeTemplate([tierS])) });

      renderEditor();

      expect(await screen.findByRole('button', { name: 'Supprimer le tier S' })).toBeDisabled();
    });

    it('shows the error code returned by the backend', async () => {
      stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(chips),
        [`DELETE ${templateUrl}/tiers/${tierB.id}`]: () => errorResponse(409, 'last_tier'),
      });
      renderEditor();

      fireEvent.click(await screen.findByRole('button', { name: 'Supprimer le tier B' }));

      expect(await screen.findByRole('alert')).toHaveTextContent(
        'Un template garde au moins un tier.',
      );
      expect(displayedTierNames()).toEqual(['S', 'A', 'B']);
    });
  });

  describe('tiles', () => {
    it('shows the tiles in template order with the tile count', async () => {
      stubBackend({ [`GET ${templateUrl}`]: () => Response.json(withTiles([pizza, sushi])) });

      renderEditor();

      expect(await screen.findByText('2 / 32 tuiles')).toBeInTheDocument();
      expect(displayedTileTexts()).toEqual(['Pizza', 'Sushi']);
    });

    it('adds a text tile at the end', async () => {
      const fetchMock: BackendMock = stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(withTiles([pizza])),
        [`POST ${templateUrl}/tiles`]: () =>
          Response.json(withTiles([pizza, makeTile('Tacos', 1)]), { status: 201 }),
      });
      renderEditor();
      const newTileField: HTMLElement = await screen.findByLabelText('Texte de la nouvelle tuile');

      fireEvent.change(newTileField, { target: { value: 'Tacos' } });
      fireEvent.click(screen.getByRole('button', { name: 'Ajouter la tuile' }));

      await waitFor(() => expect(displayedTileTexts()).toEqual(['Pizza', 'Tacos']));
      await expect(requestBody(fetchMock, 'POST')).resolves.toEqual({ text: 'Tacos' });
      // Le champ est vidé pour la tuile suivante
      expect(newTileField).toHaveValue('');
    });

    it('shows the field error when the new tile is blank', async () => {
      stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(withTiles([])),
        [`POST ${templateUrl}/tiles`]: () =>
          errorResponse(422, 'validation_error', {
            errors: [
              {
                field: 'body.text',
                message: 'String should have at least 1 character',
                code: 'string_too_short',
                params: { min_length: 1 },
              },
            ],
          }),
      });
      renderEditor();
      const newTileField: HTMLElement = await screen.findByLabelText('Texte de la nouvelle tuile');

      fireEvent.change(newTileField, { target: { value: '   ' } });
      fireEvent.click(screen.getByRole('button', { name: 'Ajouter la tuile' }));

      expect(await screen.findByText('Au moins 1 caractères.')).toBeInTheDocument();
      expect(newTileField).toHaveAttribute('aria-invalid', 'true');
      expect(displayedTileTexts()).toEqual([]);
    });

    it('shows the limit sent by the backend when the template is full', async () => {
      stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(withTiles([pizza])),
        [`POST ${templateUrl}/tiles`]: () =>
          errorResponse(409, 'tile_limit_reached', { params: { max_tiles: 32 } }),
      });
      renderEditor();

      fireEvent.change(await screen.findByLabelText('Texte de la nouvelle tuile'), {
        target: { value: 'Tacos' },
      });
      fireEvent.click(screen.getByRole('button', { name: 'Ajouter la tuile' }));

      expect(await screen.findByRole('alert')).toHaveTextContent(
        'Un template a au plus 32 tuiles.',
      );
    });

    it('disables adding once the template has its maximum number of tiles', async () => {
      const fullTemplate: Template = { ...withTiles([pizza, sushi]), max_tiles: 2 };
      stubBackend({ [`GET ${templateUrl}`]: () => Response.json(fullTemplate) });

      renderEditor();

      expect(await screen.findByText('Un template a au plus 2 tuiles.')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Ajouter la tuile' })).toBeDisabled();
      expect(screen.getByLabelText('Texte de la nouvelle tuile')).toBeDisabled();
    });

    it('edits the text of a tile', async () => {
      const fetchMock: BackendMock = stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(withTiles([pizza])),
        [`PATCH ${templateUrl}/tiles/${pizza.id}`]: () =>
          Response.json(withTiles([{ ...pizza, text: 'Pizza 4 fromages' }])),
      });
      renderEditor();
      const tileText: HTMLElement = await screen.findByRole('textbox', {
        name: 'Texte de la tuile 1',
      });

      fireEvent.change(tileText, { target: { value: 'Pizza 4 fromages' } });
      fireEvent.submit(tileText);

      await waitFor(() => expect(displayedTileTexts()).toEqual(['Pizza 4 fromages']));
      await expect(requestBody(fetchMock, 'PATCH')).resolves.toEqual({ text: 'Pizza 4 fromages' });
    });

    it('moves a tile with the move after button', async () => {
      const fetchMock: BackendMock = stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(withTiles([pizza, sushi])),
        [`PATCH ${templateUrl}/tiles/${pizza.id}`]: () => Response.json(withTiles([sushi, pizza])),
      });
      renderEditor();

      fireEvent.click(await screen.findByRole('button', { name: 'Déplacer Pizza après' }));

      await waitFor(() => expect(displayedTileTexts()).toEqual(['Sushi', 'Pizza']));
      await expect(requestBody(fetchMock, 'PATCH')).resolves.toEqual({ position: 1 });
    });

    it('deletes a tile', async () => {
      stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(withTiles([pizza, sushi])),
        [`DELETE ${templateUrl}/tiles/${pizza.id}`]: () => Response.json(withTiles([sushi])),
      });
      renderEditor();

      fireEvent.click(await screen.findByRole('button', { name: 'Supprimer la tuile Pizza' }));

      await waitFor(() => expect(displayedTileTexts()).toEqual(['Sushi']));
      expect(screen.getByText('1 / 32 tuiles')).toBeInTheDocument();
    });
  });
  describe('editing safeguards', () => {
    it('shows a tile text error only under its field', async () => {
      stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(withTiles([pizza])),
        [`PATCH ${templateUrl}/tiles/${pizza.id}`]: () =>
          errorResponse(422, 'validation_error', {
            errors: [
              {
                field: 'body.text',
                message: 'String should have at least 1 character',
                code: 'string_too_short',
                params: { min_length: 1 },
              },
            ],
          }),
      });
      renderEditor();
      const tileText: HTMLElement = await screen.findByRole('textbox', {
        name: 'Texte de la tuile 1',
      });

      fireEvent.change(tileText, { target: { value: '   ' } });
      fireEvent.blur(tileText);

      expect(await screen.findByText('Au moins 1 caractères.')).toBeInTheDocument();
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it('disables the drag and drop of tiles while a tile move is being saved', async () => {
      stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(withTiles([pizza, sushi])),
        // L'enregistrement du déplacement ne répond jamais : il reste en cours
        [`PATCH ${templateUrl}/tiles/${pizza.id}`]: () => new Promise<Response>(() => {}),
      });
      renderEditor();

      fireEvent.click(await screen.findByRole('button', { name: 'Déplacer Pizza après' }));

      await waitFor(() =>
        expect(screen.getByRole('button', { name: 'Déplacer Sushi' })).toHaveAttribute(
          'aria-disabled',
          'true',
        ),
      );
    });

    it('sends the name once when Enter is followed by leaving the field', async () => {
      const fetchMock: BackendMock = stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(chips),
        [`PATCH ${templateUrl}`]: () =>
          Response.json(makeTemplate([tierS, tierA, tierB], 'Crisps')),
      });
      renderEditor();
      const nameField: HTMLElement = await screen.findByRole('textbox', {
        name: 'Nom du template',
      });

      fireEvent.change(nameField, { target: { value: 'Crisps' } });
      fireEvent.submit(nameField);
      fireEvent.blur(nameField);

      await screen.findByRole('heading', { name: 'Crisps' });
      expect(calledRoutes(fetchMock)).toEqual([`GET ${templateUrl}`, `PATCH ${templateUrl}`]);
    });

    it('sends the name again when it is validated after a failed save', async () => {
      const consoleError: MockInstance<typeof console.error> = vi
        .spyOn(console, 'error')
        .mockImplementation(() => {});
      let attempts: number = 0;
      const fetchMock: BackendMock = stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(chips),
        [`PATCH ${templateUrl}`]: () => {
          attempts += 1;
          return attempts === 1
            ? errorResponse(500, 'internal_error')
            : Response.json(makeTemplate([tierS, tierA, tierB], 'Crisps'));
        },
      });
      renderEditor();
      const nameField: HTMLElement = await screen.findByRole('textbox', {
        name: 'Nom du template',
      });

      fireEvent.change(nameField, { target: { value: 'Crisps' } });
      fireEvent.submit(nameField);
      await screen.findByRole('alert');
      fireEvent.submit(nameField);

      expect(await screen.findByRole('heading', { name: 'Crisps' })).toBeInTheDocument();
      expect(calledRoutes(fetchMock).filter((route) => route.startsWith('PATCH'))).toHaveLength(2);
      consoleError.mockRestore();
    });

    it('shows a field error only under its field', async () => {
      stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(chips),
        [`PATCH ${templateUrl}/tiers/${tierS.id}`]: () =>
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
      renderEditor();
      const firstTierName: HTMLElement = await screen.findByRole('textbox', {
        name: 'Nom du tier 1',
      });

      fireEvent.change(firstTierName, { target: { value: '   ' } });
      fireEvent.blur(firstTierName);

      expect(await screen.findByText('Au moins 1 caractères.')).toBeInTheDocument();
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it('disables drag and drop while a move is being saved', async () => {
      stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(chips),
        // L'enregistrement du déplacement ne répond jamais : il reste en cours
        [`PATCH ${templateUrl}/tiers/${tierS.id}`]: () => new Promise<Response>(() => {}),
      });
      renderEditor();
      const dragHandle: HTMLElement = await screen.findByRole('button', { name: 'Déplacer S' });
      expect(dragHandle).toHaveAttribute('aria-disabled', 'false');

      fireEvent.click(screen.getByRole('button', { name: 'Descendre S' }));

      await waitFor(() =>
        expect(screen.getByRole('button', { name: 'Déplacer B' })).toHaveAttribute(
          'aria-disabled',
          'true',
        ),
      );
    });

    it('keeps the pick-up announcement when a tier is picked up with the keyboard', async () => {
      stubBackend({ [`GET ${templateUrl}`]: () => Response.json(chips) });
      renderEditor();
      const dragHandle: HTMLElement = await screen.findByRole('button', { name: 'Déplacer S' });

      fireEvent.keyDown(dragHandle, { code: 'Space', key: ' ' });

      await waitFor(() =>
        expect(document.querySelector('[aria-live="assertive"]')).toHaveTextContent(
          'S saisi, position 1 sur 3.',
        ),
      );
    });

    it('restores the color when it cannot be saved', async () => {
      const consoleError: MockInstance<typeof console.error> = vi
        .spyOn(console, 'error')
        .mockImplementation(() => {});
      stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(chips),
        [`PATCH ${templateUrl}/tiers/${tierA.id}`]: () => errorResponse(500, 'internal_error'),
      });
      renderEditor();
      const colorField: HTMLElement = await screen.findByLabelText('Couleur du tier A');

      fireEvent.change(colorField, { target: { value: '#112233' } });

      expect(await screen.findByRole('alert')).toHaveTextContent('Erreur interne du serveur');
      await waitFor(() => expect(colorField).toHaveValue(tierA.color.toLowerCase()));
      consoleError.mockRestore();
    });
  });
});
