import { fireEvent, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { useCurrentUser } from '../api/auth';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import {
  alice,
  calledRoutes,
  errorResponse,
  signedInSession,
  stubBackend,
} from '../test/stubBackend';
import { VerifyEmailPage } from './VerifyEmailPage';

function renderVerifyEmailPage(path = '/verify-email?token=link-token') {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={[path]}>
      <VerifyEmailPage />
    </MemoryRouter>,
  );
}

function SignedInUserAddressStatus() {
  const { data: user } = useCurrentUser();
  if (user === undefined || user === null) return null;
  return <p>{user.email_verified ? 'Adresse confirmée' : 'Adresse à confirmer'}</p>;
}

describe('VerifyEmailPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('waits for a click, so that a mail scanner opening the link confirms nothing', () => {
    const fetchMock = stubBackend({});

    renderVerifyEmailPage();

    expect(screen.getByRole('button', { name: 'Confirmer mon adresse' })).toBeInTheDocument();
    expect(calledRoutes(fetchMock)).toEqual([]);
  });

  it('confirms the address with the token of the link', async () => {
    const fetchMock = stubBackend({
      'POST /auth/email/verify': () => new Response(null, { status: 204 }),
    });
    renderVerifyEmailPage();

    fireEvent.click(screen.getByRole('button', { name: 'Confirmer mon adresse' }));

    expect(await screen.findByRole('status')).toHaveTextContent(
      'Votre adresse e-mail est confirmée.',
    );
    expect(screen.getByRole('link', { name: 'Continuer' })).toHaveAttribute('href', '/');
    await expect(fetchMock.mock.calls[0][0].json()).resolves.toEqual({ token: 'link-token' });
  });

  it('shows the address as confirmed to the user signed in on this browser', async () => {
    let emailVerified: boolean = false;
    stubBackend({
      ...signedInSession,
      'GET /auth/me': () => Response.json({ ...alice, email_verified: emailVerified }),
      'POST /auth/email/verify': () => {
        emailVerified = true;
        return new Response(null, { status: 204 });
      },
    });
    renderWithQueryClient(
      <MemoryRouter initialEntries={['/verify-email?token=link-token']}>
        <VerifyEmailPage />
        <SignedInUserAddressStatus />
      </MemoryRouter>,
    );
    expect(await screen.findByText('Adresse à confirmer')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Confirmer mon adresse' }));

    expect(await screen.findByText('Adresse confirmée')).toBeInTheDocument();
  });

  it('explains an invalid or expired link', async () => {
    stubBackend({ 'POST /auth/email/verify': () => errorResponse(400, 'invalid_token') });
    renderVerifyEmailPage();

    fireEvent.click(screen.getByRole('button', { name: 'Confirmer mon adresse' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Ce lien est invalide ou a expiré.');
  });

  it('explains a link without token', () => {
    stubBackend({});

    renderVerifyEmailPage('/verify-email');

    expect(screen.getByRole('alert')).toHaveTextContent('Ce lien est incomplet');
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
