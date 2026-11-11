import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { setAccessToken } from '../api/client';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import {
  alice,
  calledRoutes,
  signedInSession,
  stubBackend,
  unverifiedAlice,
  unverifiedSession,
} from '../test/stubBackend';
import { EmailVerificationBanner } from './EmailVerificationBanner';

const pendingText: string = 'Confirmez votre adresse : un lien a été envoyé à alice@example.com.';

describe('EmailVerificationBanner', () => {
  afterEach(() => {
    setAccessToken(null);
    vi.unstubAllGlobals();
  });

  it('asks to confirm an unverified address, still unverified once read again', async () => {
    const fetchMock = stubBackend(unverifiedSession);

    renderWithQueryClient(<EmailVerificationBanner />, { currentUser: unverifiedAlice });

    expect(screen.getByText(pendingText)).toBeInTheDocument();
    await waitFor(() => expect(calledRoutes(fetchMock)).toContain('GET /auth/me'));
    expect(screen.getByText(pendingText)).toBeInTheDocument();
  });

  it('sends the email again in the interface language', async () => {
    const fetchMock = stubBackend({
      ...unverifiedSession,
      'POST /auth/email/verification': () => new Response(null, { status: 204 }),
    });
    renderWithQueryClient(<EmailVerificationBanner />, { currentUser: unverifiedAlice });

    fireEvent.click(screen.getByRole('button', { name: "Renvoyer l'e-mail" }));

    expect(await screen.findByRole('status')).toHaveTextContent('E-mail envoyé.');
    const verificationCall: [request: Request] | undefined = fetchMock.mock.calls.find(
      ([request]) => new URL(request.url).pathname.endsWith('/auth/email/verification'),
    );
    await expect(verificationCall?.[0].json()).resolves.toEqual({ language: 'fr' });
  });

  it('hides itself once the account read again has a confirmed email', async () => {
    const fetchMock = stubBackend(signedInSession);

    renderWithQueryClient(<EmailVerificationBanner />, { currentUser: unverifiedAlice });

    await waitFor(() => expect(screen.queryByText(pendingText)).not.toBeInTheDocument());
    expect(calledRoutes(fetchMock)).toContain('GET /auth/me');
  });

  it('shows nothing once the address is confirmed, without reading the account again', () => {
    const fetchMock = stubBackend({});

    const { container } = renderWithQueryClient(<EmailVerificationBanner />, {
      currentUser: alice,
    });

    expect(container).toBeEmptyDOMElement();
    expect(calledRoutes(fetchMock)).toEqual([]);
  });
});
