import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, type MockInstance, vi } from 'vitest';

import type { Template, Tier } from '../api/templates';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { calledRoutes, errorResponse, stubBackend } from '../test/stubBackend';
import { TemplateEditorPage } from './TemplateEditorPage';

type BackendMock = ReturnType<typeof stubBackend>;

const templateId: string = '5d0c2a8e-1f3b-4c7a-9e21-3a4b5c6d7e01';
const templateUrl: string = `/templates/${templateId}`;

function makeTier(name: string, position: number, color = '#FF7F7F'): Tier {
  return { id: `tier-${name}`, name, color, position };
}

function makeTemplate(tiers: Tier[], name = 'Chips'): Template {
  return {
    id: templateId,
    name,
    created_at: '2026-10-05T12:00:00Z',
    updated_at: '2026-10-05T12:00:00Z',
    tiers: tiers.map((tier, position) => ({ ...tier, position })),
    tiles: [],
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

  describe('editing safeguards', () => {
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
