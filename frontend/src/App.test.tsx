import { screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import App from './App';
import { renderWithQueryClient } from './test/renderWithQueryClient';

// Seul fetch est remplacé : client API, hook useHello et TanStack Query tournent pour de vrai, sans appeler le backend
function stubFetch(response: Promise<Response>) {
  vi.stubGlobal('fetch', vi.fn().mockReturnValue(response));
}

describe('App', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('shows a loading message while the backend answers', () => {
    stubFetch(new Promise(() => {}));

    renderWithQueryClient(<App />);

    expect(screen.getByText('Chargement…')).toBeInTheDocument();
  });

  it('shows the message returned by the backend', async () => {
    stubFetch(Promise.resolve(Response.json({ message: 'Hello World' })));

    renderWithQueryClient(<App />);

    expect(await screen.findByRole('heading', { name: 'Hello World' })).toBeInTheDocument();
  });

  it('shows an alert when the backend cannot be reached', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    stubFetch(Promise.resolve(new Response(null, { status: 500 })));

    renderWithQueryClient(<App />);

    expect(await screen.findByRole('alert')).toHaveTextContent('Impossible de joindre le backend');
    expect(consoleError).toHaveBeenCalled();
    consoleError.mockRestore();
  });
});
