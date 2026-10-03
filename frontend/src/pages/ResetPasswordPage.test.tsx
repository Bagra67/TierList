import { fireEvent, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { hasAccessToken, setAccessToken } from '../api/client';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { errorResponse, stubBackend } from '../test/stubBackend';
import { ResetPasswordPage } from './ResetPasswordPage';

function renderResetPasswordPage(path = '/reset-password?token=link-token') {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={[path]}>
      <ResetPasswordPage />
    </MemoryRouter>,
  );
}

function submit(password: string) {
  fireEvent.change(screen.getByLabelText('Nouveau mot de passe'), { target: { value: password } });
  fireEvent.click(screen.getByRole('button', { name: 'Changer le mot de passe' }));
}

describe('ResetPasswordPage', () => {
  afterEach(() => {
    setAccessToken(null);
    vi.unstubAllGlobals();
  });

  it('changes the password and forgets the session of this browser', async () => {
    setAccessToken('old-session-token');
    const fetchMock = stubBackend({
      'POST /auth/password/reset': () => new Response(null, { status: 204 }),
    });
    renderResetPasswordPage();

    submit('a brand new passphrase');

    expect(await screen.findByRole('status')).toHaveTextContent('Votre mot de passe a été changé.');
    expect(screen.getByRole('link', { name: 'Se connecter' })).toHaveAttribute('href', '/login');
    expect(hasAccessToken()).toBe(false);
    await expect(fetchMock.mock.calls[0][0].json()).resolves.toEqual({
      token: 'link-token',
      password: 'a brand new passphrase',
    });
  });

  it('explains an invalid, expired or already used link', async () => {
    stubBackend({ 'POST /auth/password/reset': () => errorResponse(400, 'invalid_token') });
    renderResetPasswordPage();

    submit('a brand new passphrase');

    expect(await screen.findByRole('alert')).toHaveTextContent('Ce lien est invalide ou a expiré.');
  });

  it('shows the minimum length sent by the backend next to the field', async () => {
    stubBackend({
      'POST /auth/password/reset': () =>
        errorResponse(422, 'validation_error', {
          errors: [
            {
              field: 'body.password',
              code: 'password_too_short',
              message: 'too short',
              params: { min_length: 12 },
            },
          ],
        }),
    });
    renderResetPasswordPage();

    submit('short');

    expect(
      await screen.findByText('Le mot de passe doit contenir au moins 12 caractères'),
    ).toBeInTheDocument();
  });

  it('explains a link without token', () => {
    stubBackend({});

    renderResetPasswordPage('/reset-password');

    expect(screen.getByRole('alert')).toHaveTextContent('Ce lien est incomplet');
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
