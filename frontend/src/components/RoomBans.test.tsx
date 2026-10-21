import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { Room } from '../api/rooms';
import { aliceRoom } from '../test/fixtures/rooms';
import { renderRoomPage } from '../test/renderRoomPage';
import { stubBackend } from '../test/stubBackend';

// Salle d'Alice, room admin, qui a banni Bob (compte) et Lou (invité)
const roomWithBans: Room = {
  ...aliceRoom,
  participants: [aliceRoom.participants[0]],
  bans: [
    { id: 'ban-bob', display_name: 'Bob', is_guest: false },
    { id: 'ban-lou', display_name: 'Lou', is_guest: true },
  ],
};

describe('RoomBans', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('lists the banned people and unbans one', async () => {
    stubBackend({
      'GET /rooms/K7P2QX': () => Response.json(roomWithBans),
      'DELETE /rooms/K7P2QX/bans/ban-bob': () =>
        Response.json({ ...roomWithBans, bans: [roomWithBans.bans[1]] }),
    });
    renderRoomPage();

    expect(await screen.findByRole('heading', { name: 'Bannis (2)' })).toBeInTheDocument();
    expect(screen.getByText('Lou').closest('li')).toHaveTextContent('Lou(invité)');
    fireEvent.click(screen.getByRole('button', { name: 'Débannir Bob' }));

    expect(await screen.findByRole('heading', { name: 'Bannis (1)' })).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText('Bob')).not.toBeInTheDocument());
  });

  it('shows nothing without bans', async () => {
    stubBackend({ 'GET /rooms/K7P2QX': () => Response.json(aliceRoom) });
    renderRoomPage();

    await screen.findByRole('heading', { name: 'Salle K7P2QX' });
    expect(screen.queryByRole('heading', { name: /^Bannis/ })).not.toBeInTheDocument();
  });
});
