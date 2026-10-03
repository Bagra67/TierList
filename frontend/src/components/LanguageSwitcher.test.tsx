import { fireEvent, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import App from '../App';
import { LANGUAGE_STORAGE_KEY } from '../constants/i18n';
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

describe('LanguageSwitcher', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('shows the current language', () => {
    renderLoginPage();

    expect(screen.getByLabelText('Langue')).toHaveValue('fr');
  });

  it('translates the page and remembers the choice', async () => {
    renderLoginPage();

    fireEvent.change(screen.getByLabelText('Langue'), { target: { value: 'en' } });

    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument();
    expect(screen.getByLabelText('Language')).toHaveValue('en');
    expect(localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe('en');
    expect(document.documentElement.lang).toBe('en');
  });
});
