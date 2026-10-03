import { fireEvent, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import App from '../App';
import { DARK_CLASS, THEME_STORAGE_KEY } from '../constants/theme';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { stubBackend, unauthorized } from '../test/stubBackend';

function renderLoginPage() {
  stubBackend({ 'POST /auth/refresh': unauthorized });
  return renderWithQueryClient(
    <MemoryRouter initialEntries={['/login']}>
      <App />
    </MemoryRouter>,
  );
}

describe('ThemeSwitcher', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('follows the system theme by default', () => {
    renderLoginPage();

    expect(screen.getByLabelText('Thème')).toHaveValue('system');
  });

  it('switches to dark and back to light, and remembers the choice', () => {
    renderLoginPage();
    const select = screen.getByLabelText('Thème');

    fireEvent.change(select, { target: { value: 'dark' } });

    expect(select).toHaveValue('dark');
    expect(document.documentElement).toHaveClass(DARK_CLASS);
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('dark');

    fireEvent.change(select, { target: { value: 'light' } });

    expect(document.documentElement).not.toHaveClass(DARK_CLASS);
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('light');
  });
});
