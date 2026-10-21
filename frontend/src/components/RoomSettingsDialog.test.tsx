import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { Room } from '../api/rooms';
import { aliceRoom } from '../test/fixtures/rooms';
import { renderRoomPage, settingsSummary } from '../test/renderRoomPage';
import { errorResponse, stubBackend, type BackendMock } from '../test/stubBackend';

// Corps de l'unique PATCH des réglages reçu par le faux backend, une fois envoyé
async function sentChanges(fetchMock: BackendMock): Promise<unknown> {
  const request: Request = await waitFor(() => {
    const patch = fetchMock.mock.calls.find(([call]) => call.method === 'PATCH');
    if (patch === undefined) throw new Error('No PATCH request yet');
    return patch[0];
  });
  return request.clone().json();
}

// Ouvre le lobby de la salle, puis le formulaire des réglages
async function openSettings(room: Room, routes: Parameters<typeof stubBackend>[0] = {}) {
  const fetchMock: BackendMock = stubBackend({
    'GET /rooms/K7P2QX': () => Response.json(room),
    ...routes,
  });
  renderRoomPage();
  fireEvent.click(await screen.findByRole('button', { name: 'Modifier' }));
  const dialog: HTMLElement = screen.getByRole('dialog', { name: 'Réglages de la salle' });
  return { fetchMock, dialog };
}

describe('RoomSettingsDialog', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('saves the new settings and shows them in the lobby', async () => {
    const savedRoom: Room = {
      ...aliceRoom,
      settings: {
        ...aliceRoom.settings,
        item_order: 'random',
        auto_advance: 'timer',
        timer_seconds: 20,
        admin_plays: false,
      },
    };
    const { fetchMock, dialog } = await openSettings(aliceRoom, {
      'PATCH /rooms/K7P2QX/settings': () => Response.json(savedRoom),
    });
    const timer: HTMLElement = within(dialog).getByLabelText('Durée du timer (secondes)');
    expect(timer).toBeDisabled();

    fireEvent.click(within(dialog).getByLabelText('Aléatoire'));
    fireEvent.click(within(dialog).getByLabelText('Timer par item'));
    fireEvent.change(timer, { target: { value: '20' } });
    fireEvent.click(within(dialog).getByLabelText('Je joue aussi'));
    fireEvent.click(within(dialog).getByRole('button', { name: 'Enregistrer' }));

    expect(await screen.findByText('Timer de 20 s par item')).toBeInTheDocument();
    expect(within(settingsSummary()).getByText('Ordre aléatoire')).toBeInTheDocument();
    expect(within(settingsSummary()).getByText('Le room admin ne joue pas')).toBeInTheDocument();
    expect(await sentChanges(fetchMock)).toEqual({
      item_order: 'random',
      auto_advance: 'timer',
      timer_seconds: 20,
      cooldown_seconds: 60,
      admin_plays: false,
      late_arrivals_allowed: true,
    });
  });

  it('does not send the timer duration without the timer', async () => {
    const { fetchMock, dialog } = await openSettings(aliceRoom, {
      'PATCH /rooms/K7P2QX/settings': () => Response.json(aliceRoom),
    });

    fireEvent.click(within(dialog).getByRole('button', { name: 'Enregistrer' }));

    expect(await sentChanges(fetchMock)).not.toHaveProperty('timer_seconds');
  });

  it('shows the bound sent by the backend under a duration out of bounds', async () => {
    const timerRoom: Room = {
      ...aliceRoom,
      settings: { ...aliceRoom.settings, auto_advance: 'timer' },
    };
    const { dialog } = await openSettings(timerRoom, {
      'PATCH /rooms/K7P2QX/settings': () =>
        errorResponse(422, 'validation_error', {
          errors: [
            {
              field: 'body.timer_seconds',
              message: 'Input should be greater than or equal to 5',
              code: 'greater_than_equal',
              params: { ge: 5 },
            },
          ],
        }),
    });

    fireEvent.change(within(dialog).getByLabelText('Durée du timer (secondes)'), {
      target: { value: '2' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Enregistrer' }));

    expect(await within(dialog).findByText('Au moins 5.')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('Durée du timer (secondes)')).toHaveAttribute(
      'aria-invalid',
      'true',
    );
  });

  it('only lets the late arrivals change during a game', async () => {
    const playingRoom: Room = { ...aliceRoom, status: 'playing' };
    const { fetchMock, dialog } = await openSettings(playingRoom, {
      'PATCH /rooms/K7P2QX/settings': () =>
        Response.json({
          ...playingRoom,
          settings: { ...playingRoom.settings, late_arrivals_allowed: false },
        }),
    });
    expect(within(dialog).getByLabelText('Aléatoire')).toBeDisabled();
    expect(within(dialog).getByLabelText('Cooldown final (secondes)')).toBeDisabled();
    expect(within(dialog).getByLabelText('Je joue aussi')).toBeDisabled();

    fireEvent.click(within(dialog).getByLabelText('Autoriser les arrivées pendant la partie'));
    fireEvent.click(within(dialog).getByRole('button', { name: 'Enregistrer' }));

    expect(await screen.findByText('Arrivées bloquées pendant la partie')).toBeInTheDocument();
    expect(await sentChanges(fetchMock)).toEqual({ late_arrivals_allowed: false });
  });

  it('cancels without sending anything', async () => {
    const { fetchMock, dialog } = await openSettings(aliceRoom);

    fireEvent.click(within(dialog).getByLabelText('Aléatoire'));
    fireEvent.click(within(dialog).getByRole('button', { name: 'Annuler' }));

    expect(fetchMock.mock.calls.some(([request]) => request.method === 'PATCH')).toBe(false);
    expect(within(settingsSummary()).getByText('Ordre du template')).toBeInTheDocument();
  });
});
