import { fireEvent, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { stubBackend } from '../test/stubBackend';
import { ForgotPasswordPage } from './ForgotPasswordPage';

function renderForgotPasswordPage() {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={['/forgot-password']}>
      <ForgotPasswordPage />
    </MemoryRouter>,
  );
}

describe('ForgotPasswordPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('asks for a link and shows the same message whether the account exists or not', async () => {
    const fetchMock = stubBackend({
      'POST /auth/password/forgot': () => new Response(null, { status: 204 }),
    });
    renderForgotPasswordPage();

    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'alice@example.com' } });
    fireEvent.click(screen.getByRole('button', { name: 'Envoyer le lien' }));

    expect(await screen.findByRole('status')).toHaveTextContent(
      'Si un compte existe pour cette adresse',
    );
    await expect(fetchMock.mock.calls[0][0].json()).resolves.toEqual({
      email: 'alice@example.com',
      language: 'fr',
    });
  });

  it('links back to the sign-in page', () => {
    stubBackend({});

    renderForgotPasswordPage();

    expect(screen.getByRole('link', { name: 'Retour à la connexion' })).toHaveAttribute(
      'href',
      '/login',
    );
  });
});
