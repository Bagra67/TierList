import { fireEvent, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { User } from '../api/auth';
import { setAccessToken } from '../api/client';
import { renderWithQueryClient } from '../test/renderWithQueryClient';
import { alice, calledRoutes, stubBackend } from '../test/stubBackend';
import { EmailVerificationBanner } from './EmailVerificationBanner';

const unverifiedAlice: User = { ...alice, email_verified: false };

describe('EmailVerificationBanner', () => {
  afterEach(() => {
    setAccessToken(null);
    vi.unstubAllGlobals();
  });

  it('asks to confirm an unverified address', () => {
    stubBackend({});

    renderWithQueryClient(<EmailVerificationBanner user={unverifiedAlice} />);

    expect(
      screen.getByText('Confirmez votre adresse : un lien a été envoyé à alice@example.com.'),
    ).toBeInTheDocument();
  });

  it('sends the email again in the interface language', async () => {
    const fetchMock = stubBackend({
      'POST /auth/email/verification': () => new Response(null, { status: 204 }),
    });
    renderWithQueryClient(<EmailVerificationBanner user={unverifiedAlice} />);

    fireEvent.click(screen.getByRole('button', { name: "Renvoyer l'email" }));

    expect(await screen.findByRole('status')).toHaveTextContent('Email envoyé.');
    expect(calledRoutes(fetchMock)).toEqual(['POST /auth/email/verification']);
    await expect(fetchMock.mock.calls[0][0].json()).resolves.toEqual({ language: 'fr' });
  });

  it('shows nothing once the address is confirmed', () => {
    stubBackend({});

    const { container } = renderWithQueryClient(<EmailVerificationBanner user={alice} />);

    expect(container).toBeEmptyDOMElement();
  });
});
