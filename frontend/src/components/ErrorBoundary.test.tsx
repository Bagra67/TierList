import type { ErrorEvent } from '@sentry/react';
import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { captureSentryEvents } from '../test/sentryEvents';
import { ErrorBoundary } from './ErrorBoundary';

function Broken(): never {
  throw new Error('render failed');
}

describe('ErrorBoundary', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('renders its children when nothing fails', () => {
    render(
      <ErrorBoundary>
        <p>Contenu</p>
      </ErrorBoundary>,
    );

    expect(screen.getByText('Contenu')).toBeInTheDocument();
  });

  it('replaces a crashed page with a message and a reload button', () => {
    const silencedReactErrorLog = vi.spyOn(console, 'error').mockImplementation(() => {});
    const reload = vi.fn();
    vi.stubGlobal('location', { ...window.location, reload });

    render(
      <ErrorBoundary>
        <Broken />
      </ErrorBoundary>,
    );

    expect(screen.getByRole('heading', { name: 'Une erreur est survenue' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Recharger la page' }));
    expect(reload).toHaveBeenCalledOnce();
    expect(silencedReactErrorLog).toHaveBeenCalled();
  });

  it('reports the crash to Sentry with the component stack', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const events: ErrorEvent[] = captureSentryEvents();

    render(
      <ErrorBoundary>
        <Broken />
      </ErrorBoundary>,
    );

    await vi.waitFor(() => expect(events).toHaveLength(1));
    expect(events[0].exception?.values?.[0].value).toBe('render failed');
    expect(events[0].contexts?.react?.componentStack).toContain('Broken');
  });
});
