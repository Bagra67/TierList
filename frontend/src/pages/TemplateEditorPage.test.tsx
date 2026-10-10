import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, type MockInstance, vi } from 'vitest';

import type { UploadedImage } from '../api/images';
import type { Template, Tier, Tile } from '../api/templates';
import { type FileDataTransfer, fileDataTransfer } from '../test/fileDataTransfer';
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
  return { id: `tile-${text}`, text, image_url: null, position };
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

    it('refuses a new tile without text nor image without calling the backend', async () => {
      const fetchMock: BackendMock = stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(withTiles([])),
      });
      renderEditor();
      const newTileField: HTMLElement = await screen.findByLabelText('Texte de la nouvelle tuile');

      fireEvent.change(newTileField, { target: { value: '   ' } });
      fireEvent.click(screen.getByRole('button', { name: 'Ajouter la tuile' }));

      expect(await screen.findByRole('alert')).toHaveTextContent(
        "Une tuile a besoin d'un texte ou d'une image.",
      );
      expect(calledRoutes(fetchMock)).toEqual([`GET ${templateUrl}`]);
    });

    it('shows the field error sent by the backend under the new tile text', async () => {
      stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(withTiles([])),
        [`POST ${templateUrl}/tiles`]: () =>
          errorResponse(422, 'validation_error', {
            errors: [
              {
                field: 'body.text',
                message: 'String should have at most 200 characters',
                code: 'string_too_long',
                params: { max_length: 200 },
              },
            ],
          }),
      });
      renderEditor();
      const newTileField: HTMLElement = await screen.findByLabelText('Texte de la nouvelle tuile');

      fireEvent.change(newTileField, { target: { value: 'Tacos' } });
      fireEvent.click(screen.getByRole('button', { name: 'Ajouter la tuile' }));

      expect(await screen.findByText('Au plus 200 caractères.')).toBeInTheDocument();
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
  describe('tile images', () => {
    const uploadedImage: UploadedImage = {
      id: '7a1c2e3f-4b5d-4e6f-8a9b-0c1d2e3f4a5b',
      url: 'https://images.example.com/tacos.webp',
      width: 512,
      height: 512,
    };
    const pizzaWithImage: Tile = { ...pizza, image_url: 'https://images.example.com/pizza.webp' };
    const imageOnlyTile: Tile = {
      id: 'tile-image-only',
      text: null,
      image_url: 'https://images.example.com/only.webp',
      position: 0,
    };

    function pngFile(name: string = 'tacos.png'): File {
      return new File(['png-bytes'], name, { type: 'image/png' });
    }

    // Champ fichier caché d'une vignette, trouvé par le nom accessible de la vignette
    function fileInputOf(zoneName: string): HTMLInputElement {
      const zone: HTMLElement = screen.getByRole('button', { name: zoneName });
      const input: HTMLInputElement | null | undefined =
        zone.parentElement?.querySelector('input[type="file"]');
      if (input === null || input === undefined) throw new Error(`no file input for ${zoneName}`);
      return input;
    }

    function dropFile(zoneName: string, file: File) {
      const zone: HTMLElement = screen.getByRole('button', { name: zoneName });
      const dataTransfer: FileDataTransfer = fileDataTransfer(file);
      fireEvent.dragEnter(zone, { dataTransfer });
      fireEvent.dragOver(zone, { dataTransfer });
      fireEvent.drop(zone, { dataTransfer });
    }

    // La requête est-elle un envoi multipart avec un champ file ? Lu dans le corps brut : sous
    // jsdom, undici ne sait ni relire ce FormData ni lire le contenu d'un File de jsdom (le
    // contenu envoyé est vérifié par les tests du backend)
    async function sendsAFileField(request: Request): Promise<boolean> {
      const contentType: string = request.headers.get('content-type') ?? '';
      const body: string = await request.text();
      return contentType.startsWith('multipart/form-data') && body.includes('name="file"');
    }

    it('shows the image of a tile', async () => {
      stubBackend({ [`GET ${templateUrl}`]: () => Response.json(withTiles([pizzaWithImage])) });

      renderEditor();

      const zone: HTMLElement = await screen.findByRole('button', {
        name: "Remplacer l'image de Pizza",
      });
      expect(zone.querySelector('img')).toHaveAttribute('src', pizzaWithImage.image_url);
    });

    it('adds a tile with an image chosen with the file picker', async () => {
      const uploads: boolean[] = [];
      const fetchMock: BackendMock = stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(withTiles([])),
        'POST /images': async (request) => {
          uploads.push(await sendsAFileField(request));
          return Response.json(uploadedImage, { status: 201 });
        },
        [`POST ${templateUrl}/tiles`]: () =>
          Response.json(
            withTiles([{ ...makeTile('Tacos', 0), text: null, image_url: uploadedImage.url }]),
            { status: 201 },
          ),
      });
      renderEditor();
      await screen.findByText('0 / 32 tuiles');

      fireEvent.change(fileInputOf('Ajouter une image à la nouvelle tuile'), {
        target: { files: [pngFile()] },
      });
      const preview: HTMLElement = await screen.findByRole('button', {
        name: "Remplacer l'image de la nouvelle tuile",
      });
      expect(preview.querySelector('img')).toHaveAttribute('src', uploadedImage.url);
      fireEvent.click(screen.getByRole('button', { name: 'Ajouter la tuile' }));

      expect(
        await screen.findByRole('button', { name: "Remplacer l'image de Tuile 1" }),
      ).toBeInTheDocument();
      expect(uploads).toEqual([true]);
      const addRequest: Request | undefined = fetchMock.mock.calls
        .map(([request]) => request)
        .find((request) => request.url.endsWith('/tiles'));
      await expect(addRequest?.json()).resolves.toEqual({ image_id: uploadedImage.id });
      // Le formulaire est vidé, image comprise, pour la tuile suivante
      expect(
        screen.getByRole('button', { name: 'Ajouter une image à la nouvelle tuile' }),
      ).toBeInTheDocument();
    });

    it('uploads an image dropped on the new tile', async () => {
      const fetchMock: BackendMock = stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(withTiles([])),
        'POST /images': () => Response.json(uploadedImage, { status: 201 }),
      });
      renderEditor();
      await screen.findByText('0 / 32 tuiles');

      dropFile('Ajouter une image à la nouvelle tuile', pngFile());

      expect(
        await screen.findByRole('button', { name: "Remplacer l'image de la nouvelle tuile" }),
      ).toBeInTheDocument();
      expect(calledRoutes(fetchMock)).toContain('POST /images');
    });

    it('replaces the image of a tile with a dropped file', async () => {
      const fetchMock: BackendMock = stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(withTiles([pizzaWithImage])),
        'POST /images': () => Response.json(uploadedImage, { status: 201 }),
        [`PATCH ${templateUrl}/tiles/${pizza.id}`]: () =>
          Response.json(withTiles([{ ...pizza, image_url: uploadedImage.url }])),
      });
      renderEditor();
      await screen.findByRole('button', { name: "Remplacer l'image de Pizza" });

      dropFile("Remplacer l'image de Pizza", pngFile());

      await waitFor(() =>
        expect(
          screen.getByRole('button', { name: "Remplacer l'image de Pizza" }).querySelector('img'),
        ).toHaveAttribute('src', uploadedImage.url),
      );
      await expect(requestBody(fetchMock, 'PATCH')).resolves.toEqual({
        image_id: uploadedImage.id,
      });
    });

    it('removes the image of a tile that has a text', async () => {
      const fetchMock: BackendMock = stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(withTiles([pizzaWithImage])),
        [`PATCH ${templateUrl}/tiles/${pizza.id}`]: () => Response.json(withTiles([pizza])),
      });
      renderEditor();

      fireEvent.click(await screen.findByRole('button', { name: "Retirer l'image de Pizza" }));

      expect(
        await screen.findByRole('button', { name: 'Ajouter une image à Pizza' }),
      ).toBeInTheDocument();
      await expect(requestBody(fetchMock, 'PATCH')).resolves.toEqual({ image_id: null });
    });

    it('keeps the image of an image-only tile, whose text is optional', async () => {
      const fetchMock: BackendMock = stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(withTiles([imageOnlyTile])),
      });
      renderEditor();

      await screen.findByRole('button', { name: "Remplacer l'image de Tuile 1" });

      // Sans texte, retirer l'image laisserait la tuile vide : le bouton n'existe pas
      expect(screen.queryByRole('button', { name: /^Retirer l'image/ })).not.toBeInTheDocument();
      expect(screen.getByRole('textbox', { name: 'Texte de la tuile 1' })).not.toBeRequired();
      expect(calledRoutes(fetchMock)).toEqual([`GET ${templateUrl}`]);
    });

    it('removes the text of a tile that has an image when its field is emptied', async () => {
      const fetchMock: BackendMock = stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(withTiles([pizzaWithImage])),
        [`PATCH ${templateUrl}/tiles/${pizza.id}`]: () =>
          Response.json(withTiles([{ ...pizzaWithImage, text: null }])),
      });
      renderEditor();
      const textField: HTMLElement = await screen.findByRole('textbox', {
        name: 'Texte de la tuile 1',
      });

      fireEvent.change(textField, { target: { value: '  ' } });
      fireEvent.blur(textField);

      await expect.poll(() => requestBody(fetchMock, 'PATCH')).toEqual({ text: null });
    });

    it('shows the size limit sent by the backend in megabytes', async () => {
      stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(withTiles([])),
        'POST /images': () =>
          errorResponse(413, 'image_too_large', { params: { max_bytes: 10485760 } }),
      });
      renderEditor();
      await screen.findByText('0 / 32 tuiles');

      fireEvent.change(fileInputOf('Ajouter une image à la nouvelle tuile'), {
        target: { files: [pngFile()] },
      });

      expect(await screen.findByRole('alert')).toHaveTextContent(
        /^L'image est trop lourde : 10\sMo au maximum\.$/,
      );
      // L'aperçu disparaît : aucune image n'est rattachée à la nouvelle tuile
      expect(
        screen.getByRole('button', { name: 'Ajouter une image à la nouvelle tuile' }),
      ).toBeInTheDocument();
    });

    it('refuses a file that is not a JPEG, PNG or WebP image without sending it', async () => {
      const fetchMock: BackendMock = stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(withTiles([])),
      });
      renderEditor();
      await screen.findByText('0 / 32 tuiles');

      dropFile(
        'Ajouter une image à la nouvelle tuile',
        new File(['gif'], 'anim.gif', { type: 'image/gif' }),
      );

      expect(await screen.findByRole('alert')).toHaveTextContent(
        "Ce fichier n'est pas une image JPEG, PNG ou WebP.",
      );
      expect(calledRoutes(fetchMock)).toEqual([`GET ${templateUrl}`]);
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
  });

  describe('tier color', () => {
    // Ouvre le sélecteur de couleur du tier A et renvoie son contenu
    async function openColorPicker(): Promise<HTMLElement> {
      fireEvent.click(await screen.findByRole('button', { name: 'Couleur du tier A' }));
      return screen.findByRole('dialog');
    }

    it('recolors a tier with a suggested color once the picker is closed', async () => {
      const fetchMock: BackendMock = stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(chips),
        [`PATCH ${templateUrl}/tiers/${tierA.id}`]: () =>
          Response.json(makeTemplate([tierS, { ...tierA, color: '#7FBFFF' }, tierB])),
      });
      renderEditor();
      const picker: HTMLElement = await openColorPicker();

      fireEvent.click(within(picker).getByRole('button', { name: 'Choisir #7FBFFF' }));
      expect(calledRoutes(fetchMock)).toEqual([`GET ${templateUrl}`]);
      fireEvent.click(within(picker).getByRole('button', { name: 'OK' }));

      await waitFor(() =>
        expect(calledRoutes(fetchMock)).toContain(`PATCH ${templateUrl}/tiers/${tierA.id}`),
      );
      await expect(requestBody(fetchMock, 'PATCH')).resolves.toEqual({ color: '#7FBFFF' });
    });

    it('recolors a tier with a hex code', async () => {
      const fetchMock: BackendMock = stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(chips),
        [`PATCH ${templateUrl}/tiers/${tierA.id}`]: () =>
          Response.json(makeTemplate([tierS, { ...tierA, color: '#112233' }, tierB])),
      });
      renderEditor();
      const picker: HTMLElement = await openColorPicker();

      fireEvent.change(within(picker).getByLabelText('Code hexadécimal'), {
        target: { value: '112233' },
      });
      fireEvent.click(within(picker).getByRole('button', { name: 'OK' }));

      await waitFor(() =>
        expect(calledRoutes(fetchMock)).toContain(`PATCH ${templateUrl}/tiers/${tierA.id}`),
      );
      await expect(requestBody(fetchMock, 'PATCH')).resolves.toEqual({ color: '#112233' });
    });

    it('cancels the color change with Escape', async () => {
      const fetchMock: BackendMock = stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(chips),
      });
      renderEditor();
      const picker: HTMLElement = await openColorPicker();

      fireEvent.click(within(picker).getByRole('button', { name: 'Choisir #7FBFFF' }));
      fireEvent.keyDown(picker, { key: 'Escape' });

      await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
      expect(screen.getByRole('button', { name: 'Couleur du tier A' })).toHaveStyle({
        backgroundColor: tierA.color,
      });
      expect(calledRoutes(fetchMock)).toEqual([`GET ${templateUrl}`]);
    });

    it('sends nothing when the color did not change', async () => {
      const fetchMock: BackendMock = stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(chips),
      });
      renderEditor();
      const picker: HTMLElement = await openColorPicker();

      fireEvent.click(within(picker).getByRole('button', { name: 'OK' }));

      await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
      expect(calledRoutes(fetchMock)).toEqual([`GET ${templateUrl}`]);
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
      const picker: HTMLElement = await openColorPicker();

      fireEvent.click(within(picker).getByRole('button', { name: 'Choisir #7FBFFF' }));
      fireEvent.click(within(picker).getByRole('button', { name: 'OK' }));

      expect(await screen.findByRole('alert')).toHaveTextContent('Erreur interne du serveur');
      await waitFor(() =>
        expect(screen.getByRole('button', { name: 'Couleur du tier A' })).toHaveStyle({
          backgroundColor: tierA.color,
        }),
      );
      consoleError.mockRestore();
    });

    it('labels the picker in the language of the interface', async () => {
      stubBackend({ [`GET ${templateUrl}`]: () => Response.json(chips) });
      renderEditor();
      const picker: HTMLElement = await openColorPicker();

      expect(
        within(picker).getByRole('slider', { name: 'Saturation et luminosité' }),
      ).toHaveAttribute(
        'aria-valuetext',
        expect.stringMatching(/^Saturation \d+ %, luminosité \d+ %$/),
      );
      expect(within(picker).getByRole('slider', { name: 'Teinte' })).toBeInTheDocument();
      expect(within(picker).getByRole('group', { name: 'Couleurs proposées' })).toBeInTheDocument();
    });
  });
});
