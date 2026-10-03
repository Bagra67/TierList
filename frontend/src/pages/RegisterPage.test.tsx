import { fireEvent, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { setAccessToken } from '../api/client';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { alice, errorResponse, stubBackend, tokenResponse } from '../test/stubBackend';
import { RegisterPage } from './RegisterPage';

function renderRegisterPage() {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={['/register']}>
      <Routes>
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/" element={<h1>Accueil</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

function fillAndSubmit() {
  fireEvent.change(screen.getByLabelText('Nom affiché'), { target: { value: 'Alice' } });
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'alice@example.com' } });
  fireEvent.change(screen.getByLabelText('Mot de passe'), {
    target: { value: 'correct horse battery staple' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Créer mon compte' }));
}

describe('RegisterPage', () => {
  afterEach(() => {
    setAccessToken(null);
    vi.unstubAllGlobals();
  });

  it('creates the account and opens the home page', async () => {
    const fetchMock = stubBackend({
      'POST /auth/register': tokenResponse('new-token'),
      'GET /auth/me': () => Response.json(alice),
    });
    renderRegisterPage();

    fillAndSubmit();

    expect(await screen.findByRole('heading', { name: 'Accueil' })).toBeInTheDocument();
    await expect(fetchMock.mock.calls[0][0].json()).resolves.toEqual({
      email: 'alice@example.com',
      password: 'correct horse battery staple',
      display_name: 'Alice',
    });
  });

  it('shows the backend message when the email is already used', async () => {
    stubBackend({
      'POST /auth/register': () => errorResponse(409, 'email_already_registered'),
    });
    renderRegisterPage();

    fillAndSubmit();

    expect(await screen.findByRole('alert')).toHaveTextContent('Cet email est déjà utilisé');
  });

  it('shows the minimum password length required by the backend', async () => {
    stubBackend({
      'POST /auth/register': () =>
        errorResponse(422, 'validation_error', {
          errors: [
            {
              field: 'body.password',
              message: 'The password must be at least 12 characters long',
              code: 'password_too_short',
              params: { min_length: 12 },
            },
          ],
        }),
    });
    renderRegisterPage();

    fillAndSubmit();

    expect(
      await screen.findByText('Le mot de passe doit contenir au moins 12 caractères'),
    ).toBeInTheDocument();
  });

  it('links to the Google sign-in', () => {
    stubBackend({});
    renderRegisterPage();

    expect(screen.getByRole('link', { name: 'Continuer avec Google' })).toHaveAttribute(
      'href',
      '/api/auth/google/login',
    );
  });
});
