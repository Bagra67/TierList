import { fireEvent, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { Template, Tier } from '../api/templates';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { calledRoutes, errorResponse, stubBackend } from '../test/stubBackend';
import { TemplateEditorPage } from './TemplateEditorPage';

const templateId = '5d0c2a8e-1f3b-4c7a-9e21-3a4b5c6d7e01';
const templateUrl = `/templates/${templateId}`;

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

const [tierS, tierA, tierB] = [makeTier('S', 0), makeTier('A', 1), makeTier('B', 2)];
const chips = makeTemplate([tierS, tierA, tierB]);

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

async function requestBody(fetchMock: ReturnType<typeof stubBackend>, method: string) {
  const call = fetchMock.mock.calls.find(([request]) => request.method === method);
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
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    stubBackend({ [`GET ${templateUrl}`]: () => errorResponse(404, 'template_not_found') });

    renderEditor();

    expect(await screen.findByRole('alert')).toHaveTextContent('Ce template est introuvable.');
    consoleError.mockRestore();
  });

  describe('template name', () => {
    it('renames the template when the field is validated', async () => {
      const fetchMock = stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(chips),
        [`PATCH ${templateUrl}`]: () =>
          Response.json(makeTemplate([tierS, tierA, tierB], 'Crisps')),
      });
      renderEditor();
      const nameField = await screen.findByRole('textbox', { name: 'Nom du template' });

      fireEvent.change(nameField, { target: { value: 'Crisps' } });
      fireEvent.submit(nameField);

      expect(await screen.findByRole('heading', { name: 'Crisps' })).toBeInTheDocument();
      await expect(requestBody(fetchMock, 'PATCH')).resolves.toEqual({ name: 'Crisps' });
    });

    it('sends nothing when the name did not change', async () => {
      const fetchMock = stubBackend({ [`GET ${templateUrl}`]: () => Response.json(chips) });
      renderEditor();
      const nameField = await screen.findByRole('textbox', { name: 'Nom du template' });

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
      const nameField = await screen.findByRole('textbox', { name: 'Nom du template' });

      fireEvent.change(nameField, { target: { value: '   ' } });
      fireEvent.blur(nameField);

      expect(await screen.findByText('Au moins 1 caractères.')).toBeInTheDocument();
      expect(nameField).toHaveAttribute('aria-invalid', 'true');
    });
  });

  describe('tiers', () => {
    it('renames a tier when the field loses focus', async () => {
      const fetchMock = stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(chips),
        [`PATCH ${templateUrl}/tiers/${tierS.id}`]: () =>
          Response.json(makeTemplate([{ ...tierS, name: 'Top' }, tierA, tierB])),
      });
      renderEditor();
      const firstTierName = await screen.findByRole('textbox', { name: 'Nom du tier 1' });

      fireEvent.change(firstTierName, { target: { value: 'Top' } });
      fireEvent.blur(firstTierName);

      await waitFor(() => expect(displayedTierNames()).toEqual(['Top', 'A', 'B']));
      await expect(requestBody(fetchMock, 'PATCH')).resolves.toEqual({ name: 'Top' });
    });

    it('recolors a tier once the color is chosen', async () => {
      const fetchMock = stubBackend({
        [`GET ${templateUrl}`]: () => Response.json(chips),
        [`PATCH ${templateUrl}/tiers/${tierA.id}`]: () =>
          Response.json(makeTemplate([tierS, { ...tierA, color: '#112233' }, tierB])),
      });
      renderEditor();
      const colorField = await screen.findByLabelText('Couleur du tier A');

      fireEvent.change(colorField, { target: { value: '#112233' } });

      await waitFor(() =>
        expect(calledRoutes(fetchMock)).toContain(`PATCH ${templateUrl}/tiers/${tierA.id}`),
      );
      await expect(requestBody(fetchMock, 'PATCH')).resolves.toEqual({ color: '#112233' });
    });

    it('moves a tier with the move down button', async () => {
      const fetchMock = stubBackend({
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
      const fetchMock = stubBackend({
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
});
