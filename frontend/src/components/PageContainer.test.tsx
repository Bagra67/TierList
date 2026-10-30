import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { PAGE_WIDTH_CLASS, type PageWidth } from '../constants/layout';
import { PageContainer } from './PageContainer';

describe('PageContainer', () => {
  it.each(Object.entries(PAGE_WIDTH_CLASS) as [PageWidth, string][])(
    'renders the %s width as a centered main',
    (width, widthClass) => {
      render(<PageContainer width={width}>Contenu</PageContainer>);

      const main: HTMLElement = screen.getByRole('main');
      expect(main).toHaveClass('mx-auto', 'w-full', widthClass);
      expect(main).toHaveTextContent('Contenu');
    },
  );

  it('adds the layout of the page to the shared classes', () => {
    render(
      <PageContainer width="app" className="flex flex-col gap-6">
        Contenu
      </PageContainer>,
    );

    expect(screen.getByRole('main')).toHaveClass('max-w-6xl', 'flex', 'flex-col', 'gap-6');
  });
});
