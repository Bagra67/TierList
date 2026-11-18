import { act, render } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';

import i18n from '../i18n';
import { useDocumentTitle } from './useDocumentTitle';

function TitledPage({ page }: { page: string | undefined }) {
  useDocumentTitle(page);
  return null;
}

describe('useDocumentTitle', () => {
  beforeEach(() => {
    document.title = 'TierList';
  });

  it('names the tab after the page', () => {
    render(<TitledPage page="Vos modèles" />);

    expect(document.title).toBe('Vos modèles · TierList');
  });

  it('keeps the current title while the page name is unknown, then uses it', () => {
    const { rerender } = render(<TitledPage page={undefined} />);
    expect(document.title).toBe('TierList');

    rerender(<TitledPage page="Fromages" />);

    expect(document.title).toBe('Fromages · TierList');
  });

  it('gives the tab back the site title when the page goes away', () => {
    const { unmount } = render(<TitledPage page="Fromages" />);

    unmount();

    expect(document.title).toBe('TierList · Classez ensemble, en direct');
  });

  it('follows the interface language', async () => {
    const { unmount } = render(<TitledPage page="Cheeses" />);

    await act(() => i18n.changeLanguage('en'));
    unmount();

    expect(document.title).toBe('TierList · Rank together, live');
  });
});
