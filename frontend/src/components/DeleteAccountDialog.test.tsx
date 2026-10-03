import { fireEvent, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { setAccessToken } from '../api/client';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import type { User } from '../api/auth';
import { alice, calledRoutes, stubBackend, type StubbedRoute } from '../test/stubBackend';
import { DeleteAccountDialog } from './DeleteAccountDialog';

const googleOnlyAlice: User = { ...alice, has_password: false };

function renderDialog(user: User = alice, openOnMount = false) {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path="/" element={<DeleteAccountDialog user={user} openOnMount={openOnMount} />} />
        <Route path="/login" element={<h1>Connexion</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

function openAndConfirm(password: string) {
  fireEvent.click(screen.getByRole('button', { name: 'Supprimer mon compte' }));
  fireEvent.change(screen.getByLabelText('Mot de passe'), { target: { value: password } });
  fireEvent.click(screen.getByRole('button', { name: 'Supprimer définitivement' }));
}

const wrongPassword: StubbedRoute = () =>
  Response.json({ detail: 'Mot de passe incorrect' }, { status: 403 });

describe('DeleteAccountDialog', () => {
  afterEach(() => {
    setAccessToken(null);
    vi.unstubAllGlobals();
  });

  it('keeps the confirmation dialog closed until asked', () => {
    stubBackend({});
    renderDialog();

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Supprimer mon compte' }));

    expect(screen.getByRole('dialog', { name: 'Supprimer mon compte' })).toBeVisible();
  });

  it('deletes the account with the password, then opens the login page', async () => {
    const fetchMock = stubBackend({ 'DELETE /auth/me': () => new Response(null, { status: 204 }) });
    setAccessToken('some-token');
    renderDialog();

    openAndConfirm('correct horse battery staple');

    expect(await screen.findByRole('heading', { name: 'Connexion' })).toBeInTheDocument();
    expect(calledRoutes(fetchMock)).toEqual(['DELETE /auth/me']);
    await expect(fetchMock.mock.calls[0][0].json()).resolves.toEqual({
      password: 'correct horse battery staple',
    });
  });

  it('shows the backend message and stays open when the password is wrong', async () => {
    stubBackend({ 'DELETE /auth/me': wrongPassword });
    renderDialog();

    openAndConfirm('wrong password');

    expect(await screen.findByRole('alert')).toHaveTextContent('Mot de passe incorrect');
    expect(screen.getByRole('dialog')).toBeVisible();
  });

  it('closes on cancel and forgets the previous error', async () => {
    stubBackend({ 'DELETE /auth/me': wrongPassword });
    renderDialog();
    openAndConfirm('wrong password');
    await screen.findByRole('alert');

    fireEvent.click(screen.getByRole('button', { name: 'Annuler' }));

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Supprimer mon compte' }));
    // TanStack Query notifie la remise à zéro de la mutation de façon asynchrone
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
    expect(screen.getByLabelText('Mot de passe')).toHaveValue('');
  });

  it('opens at once when resuming a deletion after a Google sign-in', () => {
    stubBackend({});

    renderDialog(googleOnlyAlice, true);

    expect(screen.getByRole('dialog', { name: 'Supprimer mon compte' })).toBeVisible();
  });

  it('deletes a Google account without asking for a password', async () => {
    const fetchMock = stubBackend({ 'DELETE /auth/me': () => new Response(null, { status: 204 }) });
    renderDialog(googleOnlyAlice);

    fireEvent.click(screen.getByRole('button', { name: 'Supprimer mon compte' }));
    expect(screen.queryByLabelText('Mot de passe')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Supprimer définitivement' }));

    expect(await screen.findByRole('heading', { name: 'Connexion' })).toBeInTheDocument();
    await expect(fetchMock.mock.calls[0][0].json()).resolves.toEqual({});
  });

  it('offers to sign in again with Google when the last sign-in is too old', async () => {
    stubBackend({
      'DELETE /auth/me': () =>
        Response.json(
          { detail: 'Reconnectez-vous avec Google pour confirmer la suppression' },
          { status: 403 },
        ),
    });
    renderDialog(googleOnlyAlice);

    fireEvent.click(screen.getByRole('button', { name: 'Supprimer mon compte' }));
    fireEvent.click(screen.getByRole('button', { name: 'Supprimer définitivement' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Reconnectez-vous avec Google');
    expect(screen.getByRole('link', { name: 'Se reconnecter avec Google' })).toHaveAttribute(
      'href',
      '/api/auth/google/login?next=delete-account',
    );
  });
});
