import { screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import App from '../App';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { stubBackend, unauthorized } from '../test/stubBackend';

describe('Logo', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('links to the home page from the shared layout', async () => {
    stubBackend({ 'POST /auth/refresh': unauthorized });
    renderWithQueryClient(
      <MemoryRouter initialEntries={['/login']}>
        <App />
      </MemoryRouter>,
    );

    const logoLink: HTMLElement = await screen.findByRole('link', { name: 'TierList' });
    expect(logoLink).toHaveAttribute('href', '/');
  });
});
