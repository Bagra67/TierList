import { fireEvent, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { describe, expect, it } from 'vitest';

import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { NotFoundPage } from './NotFoundPage';

describe('NotFoundPage', () => {
  it('says the page does not exist and links to the home page', async () => {
    renderWithQueryClient(
      <MemoryRouter initialEntries={['/does-not-exist']}>
        <Routes>
          <Route path="/" element={<h1>Accueil</h1>} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByRole('heading', { name: 'Page introuvable' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('link', { name: "Retour à l'accueil" }));

    expect(await screen.findByRole('heading', { name: 'Accueil' })).toBeInTheDocument();
  });
});
