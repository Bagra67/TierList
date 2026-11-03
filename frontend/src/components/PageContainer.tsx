import { cn } from 'cn';
import type { ReactNode } from 'react';

import { PAGE_WIDTH_CLASS, type PageWidth } from '../constants/layout';

interface PageContainerProps {
  width: PageWidth;
  className?: string;
  children: ReactNode;
}

export function PageContainer({ width, className, children }: PageContainerProps) {
  return (
    <main className={cn('mx-auto w-full px-4 py-10', PAGE_WIDTH_CLASS[width], className)}>
      {children}
    </main>
  );
}
