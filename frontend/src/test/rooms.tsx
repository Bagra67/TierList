import { screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';

import type { Room } from '../api/rooms';
import { RoomPage } from '../pages/RoomPage';
import { renderWithQueryClient } from './renderWithQueryClient';

// Salle d'Alice (room admin) avec Bob, telle que la renvoie GET /rooms/{code}
export const aliceRoom: Room = {
  code: 'K7P2QX',
  link: 'http://localhost:5173/r/K7P2QX',
  status: 'open',
  template: { id: '5d0c2a8e-1f3b-4c7a-9e21-3a4b5c6d7e01', name: 'Chips' },
  settings: {
    item_order: 'template',
    auto_advance: 'none',
    timer_seconds: 30,
    cooldown_seconds: 60,
    admin_plays: true,
    late_arrivals_allowed: true,
  },
  participants: [
    {
      id: '9a1b2c3d-0000-4000-8000-000000000001',
      display_name: 'Alice',
      is_admin: true,
      is_guest: false,
    },
    {
      id: '9a1b2c3d-0000-4000-8000-000000000002',
      display_name: 'Bob',
      is_admin: false,
      is_guest: false,
    },
  ],
  is_admin: true,
};

// Lobby de la salle, ouvert par son lien
export function renderRoomPage(code: string = aliceRoom.code) {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={[`/r/${code}`]}>
      <Routes>
        <Route path="/r/:code" element={<RoomPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

// Résumé des réglages du lobby (le formulaire, fermé, contient les mêmes libellés)
export function settingsSummary(): HTMLElement {
  const section: HTMLElement | null = screen
    .getByRole('heading', { name: 'Réglages' })
    .closest('section');
  if (section === null) throw new Error('No settings section');
  return within(section).getByRole('list');
}
