import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

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
    // React journalise l'erreur attrapée : rendu silencieux pour garder la sortie lisible
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
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
    expect(consoleError).toHaveBeenCalled();
  });
});
