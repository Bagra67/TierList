import { fireEvent, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { setAccessToken } from '../api/client';
import i18n from '../i18n';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { alice, errorResponse, stubBackend, tokenResponse } from '../test/stubBackend';
import { LoginPage } from './LoginPage';

function renderLoginPage(path = '/login') {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<h1>Accueil</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

function fillAndSubmit(email: string, password: string) {
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: email } });
  fireEvent.change(screen.getByLabelText('Mot de passe'), { target: { value: password } });
  fireEvent.click(screen.getByRole('button', { name: 'Se connecter' }));
}

describe('LoginPage', () => {
  afterEach(() => {
    setAccessToken(null);
    vi.unstubAllGlobals();
  });

  it('sends the credentials and opens the home page', async () => {
    const fetchMock = stubBackend({
      'POST /auth/login': tokenResponse('login-token'),
      'GET /auth/me': () => Response.json(alice),
    });
    renderLoginPage();

    fillAndSubmit('alice@example.com', 'correct horse battery staple');

    expect(await screen.findByRole('heading', { name: 'Accueil' })).toBeInTheDocument();
    const loginRequest = fetchMock.mock.calls[0][0];
    await expect(loginRequest.json()).resolves.toEqual({
      email: 'alice@example.com',
      password: 'correct horse battery staple',
    });
  });

  it('shows the backend message when the credentials are wrong', async () => {
    stubBackend({
      'POST /auth/login': () => errorResponse(401, 'invalid_credentials'),
    });
    renderLoginPage();

    fillAndSubmit('alice@example.com', 'wrong password');

    expect(await screen.findByRole('alert')).toHaveTextContent('Email ou mot de passe incorrect');
    expect(screen.getByRole('heading', { name: 'Connexion' })).toBeInTheDocument();
  });

  it('shows the page and the backend error in English', async () => {
    await i18n.changeLanguage('en');
    stubBackend({ 'POST /auth/login': () => errorResponse(401, 'invalid_credentials') });
    renderLoginPage();

    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'alice@example.com' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'wrong password' } });
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Incorrect email or password');
    expect(screen.getByRole('heading', { name: 'Sign in' })).toBeInTheDocument();
  });

  it('disables the button while the request is pending', async () => {
    stubBackend({ 'POST /auth/login': () => new Promise<Response>(() => {}) });
    renderLoginPage();

    fillAndSubmit('alice@example.com', 'correct horse battery staple');

    expect(await screen.findByRole('button', { name: 'Connexion…' })).toBeDisabled();
  });

  it('shows validation errors next to the field', async () => {
    stubBackend({
      'POST /auth/login': () =>
        errorResponse(422, 'validation_error', {
          errors: [
            {
              field: 'body.email',
              message: 'value is not a valid email address',
              code: 'value_error',
            },
          ],
        }),
    });
    renderLoginPage();

    fillAndSubmit('alice@example', 'correct horse battery staple');

    expect(await screen.findByText('Valeur invalide.')).toBeInTheDocument();
    expect(screen.getByLabelText('Email')).toHaveAttribute('aria-invalid', 'true');
  });

  it('links to the Google sign-in', () => {
    stubBackend({});
    renderLoginPage();

    expect(screen.getByRole('link', { name: 'Continuer avec Google' })).toHaveAttribute(
      'href',
      '/api/auth/google/login',
    );
  });

  it.each([
    ['google_cancelled', 'Connexion avec Google annulée.'],
    ['google_email_not_verified', "Votre adresse Google n'est pas vérifiée"],
    ['google_unavailable', "La connexion avec Google n'est pas disponible"],
    ['google_failed', 'La connexion avec Google a échoué'],
    ['unknown_code', 'La connexion avec Google a échoué'],
  ])('explains the Google error %s', (code, message) => {
    stubBackend({});
    renderLoginPage(`/login?error=${code}`);

    expect(screen.getByRole('alert')).toHaveTextContent(message);
  });
});
