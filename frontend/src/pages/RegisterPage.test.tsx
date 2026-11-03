import { fireEvent, screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { setAccessToken } from '../api/client';
import i18n from '../i18n';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import {
  alice,
  type BackendMock,
  errorResponse,
  stubBackend,
  tokenResponse,
} from '../test/stubBackend';
import { LoginPage } from './LoginPage';
import { RegisterPage } from './RegisterPage';

function renderRegisterPage(requestedPrivatePath?: string) {
  return renderWithQueryClient(
    <MemoryRouter
      initialEntries={[{ pathname: '/register', state: { from: requestedPrivatePath } }]}
    >
      <Routes>
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<h1>Accueil</h1>} />
        <Route path="/r/K7P2QX" element={<h1>Lobby</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

function fillAndSubmit() {
  fireEvent.change(screen.getByLabelText('Nom affiché'), { target: { value: 'Alice' } });
  fireEvent.change(screen.getByLabelText('E-mail'), { target: { value: 'alice@example.com' } });
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
      language: 'fr',
    });
  });

  it('sends the interface language for the verification email', async () => {
    await i18n.changeLanguage('en');
    const fetchMock: BackendMock = stubBackend({
      'POST /auth/register': tokenResponse('new-token'),
      'GET /auth/me': () => Response.json(alice),
    });
    renderRegisterPage();

    fireEvent.change(screen.getByLabelText('Display name'), { target: { value: 'Alice' } });
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'alice@example.com' } });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'correct horse battery staple' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Create my account' }));

    expect(await screen.findByRole('heading', { name: 'Accueil' })).toBeInTheDocument();
    await expect(fetchMock.mock.calls[0][0].json()).resolves.toMatchObject({ language: 'en' });
  });

  it('keeps the requested page when the visitor goes on to sign in', async () => {
    stubBackend({
      'POST /auth/login': tokenResponse('login-token'),
      'GET /auth/me': () => Response.json(alice),
    });
    renderRegisterPage('/r/K7P2QX');

    fireEvent.click(screen.getByRole('link', { name: 'Se connecter' }));
    fireEvent.change(screen.getByLabelText('E-mail'), { target: { value: 'alice@example.com' } });
    fireEvent.change(screen.getByLabelText('Mot de passe'), {
      target: { value: 'correct horse battery staple' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Se connecter' }));

    expect(await screen.findByRole('heading', { name: 'Lobby' })).toBeInTheDocument();
  });

  it('goes back to the requested page after the sign-up', async () => {
    stubBackend({
      'POST /auth/register': tokenResponse('new-token'),
      'GET /auth/me': () => Response.json(alice),
    });
    renderRegisterPage('/r/K7P2QX');

    fillAndSubmit();

    expect(await screen.findByRole('heading', { name: 'Lobby' })).toBeInTheDocument();
  });

  it('shows the backend message when the email is already used', async () => {
    stubBackend({
      'POST /auth/register': () => errorResponse(409, 'email_already_registered'),
    });
    renderRegisterPage();

    fillAndSubmit();

    expect(await screen.findByRole('alert')).toHaveTextContent('Cet e-mail est déjà utilisé');
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

  it('says that creating an account accepts the terms and the privacy policy', () => {
    stubBackend({});
    renderRegisterPage();

    const sentence: HTMLElement = screen.getByText(/^En créant un compte, vous acceptez/);
    expect(
      within(sentence).getByRole('link', { name: "conditions d'utilisation" }),
    ).toHaveAttribute('href', '/terms');
    expect(
      within(sentence).getByRole('link', { name: 'politique de confidentialité' }),
    ).toHaveAttribute('href', '/privacy');
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
