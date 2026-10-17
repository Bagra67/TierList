import type { GuestRoom, Room } from '../../api/rooms';

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
  bans: [],
  game: null,
};

// La même salle pendant une partie : tour 1 sur 3, telle que la renvoie POST /rooms/{code}/game
export const aliceRoomInGame: Room = {
  ...aliceRoom,
  version: 4,
  status: 'playing',
  game: {
    round_number: 1,
    round_count: 3,
    current_item: {
      id: '7c1d2e3f-0000-4000-8000-000000000001',
      text: 'Paprika',
      image_url: 'https://images.example.com/paprika.webp',
    },
    ends_at: null,
  },
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
