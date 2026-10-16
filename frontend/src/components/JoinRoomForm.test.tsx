import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { describe, expect, it } from 'vitest';

import { JoinRoomForm } from './JoinRoomForm';

function renderJoinRoomForm() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path="/" element={<JoinRoomForm />} />
        <Route path="/r/K7P2QX" element={<h1>Lobby</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('JoinRoomForm', () => {
  it('opens the room of the typed code, in capitals', async () => {
    renderJoinRoomForm();

    fireEvent.change(screen.getByLabelText('Code de la salle'), {
      target: { value: '  k7p2qx ' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Rejoindre' }));

    expect(await screen.findByRole('heading', { name: 'Lobby' })).toBeInTheDocument();
  });
});
