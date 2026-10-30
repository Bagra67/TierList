import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { LoadingSkeleton } from './LoadingSkeleton';

describe('LoadingSkeleton', () => {
  it('writes the loading text once the status region is in the page', async () => {
    render(<LoadingSkeleton shape="list" />);

    const status: HTMLElement = screen.getByRole('status');
    expect(status.textContent).toBe('');
    expect(await screen.findByText('Chargement…')).toBeInTheDocument();
    expect(status).toHaveTextContent('Chargement…');
  });
});
