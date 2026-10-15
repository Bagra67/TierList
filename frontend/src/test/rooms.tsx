import { screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';

import type { GuestRoom, Room } from '../api/rooms';
import { RoomPage } from '../pages/RoomPage';
import { LocationHash } from './LocationHash';
import { renderWithQueryClient } from './renderWithQueryClient';
import { alice, type StubbedRoute, tokenResponse } from './stubBackend';

// Session d'un compte connecté (Alice) : sans elle, la page de la salle voit un visiteur
export const signedInSession: Record<string, StubbedRoute> = {
  'POST /auth/refresh': tokenResponse('alice-token'),
  'GET /auth/me': () => Response.json(alice),
};

// Salle d'Alice (room admin) avec Bob, telle que la renvoie GET /rooms/{code}
export const aliceRoom: Room = {
  code: 'K7P2QX',
  version: 3,
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
      connected: true,
    },
    {
      id: '9a1b2c3d-0000-4000-8000-000000000002',
      display_name: 'Bob',
      is_admin: false,
      is_guest: false,
      connected: false,
    },
  ],
  is_admin: true,
};

// Salle rejointe par Lou en invité, avec son lien perso, telle que la renvoie POST /guests
export const lousRoom: GuestRoom = {
  ...aliceRoom,
  is_admin: false,
  participants: [
    ...aliceRoom.participants,
    {
      id: '9a1b2c3d-0000-4000-8000-000000000003',
      display_name: 'Lou',
      is_admin: false,
      is_guest: true,
      connected: false,
    },
  ],
  guest_link: 'http://localhost:5173/r/K7P2QX#guest=lou-token',
  guest_link_expires_at: '2026-11-10T12:00:00Z',
};

// Page de la salle ouverte par son lien (path peut porter un fragment, ex. le lien perso) ;
// /login affiche un simple titre
export function renderRoomPage(path: string = aliceRoom.code) {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={[`/r/${path}`]}>
      <Routes>
        <Route
          path="/r/:code"
          element={
            <>
              <RoomPage />
              <LocationHash />
            </>
          }
        />
        <Route path="/login" element={<h1>Connexion</h1>} />
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
