import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { getHello } from './api/hello';
import App from './App';

vi.mock('./api/hello');

const mockedGetHello = vi.mocked(getHello);

describe('App', () => {
  beforeEach(() => {
    mockedGetHello.mockReset();
  });

  it('shows a loading message while the backend answers', () => {
    mockedGetHello.mockReturnValue(new Promise(() => {}));

    render(<App />);

    expect(screen.getByText('Chargement…')).toBeInTheDocument();
  });

  it('shows the message returned by the backend', async () => {
    mockedGetHello.mockResolvedValue({ message: 'Hello World' });

    render(<App />);

    expect(await screen.findByRole('heading', { name: 'Hello World' })).toBeInTheDocument();
  });

  it('shows an alert when the backend cannot be reached', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    mockedGetHello.mockRejectedValue(new Error('HTTP 500'));

    render(<App />);

    expect(await screen.findByRole('alert')).toHaveTextContent('Impossible de joindre le backend');
    expect(consoleError).toHaveBeenCalled();
    consoleError.mockRestore();
  });
});
