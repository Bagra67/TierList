import { cn } from 'cn';
import type { ReactNode } from 'react';

import { PAGE_WIDTH_CLASS, type PageWidth } from '../constants/layout';

// Racine (main) de chaque page : centrée, à l'une des trois largeurs de constants/layout.ts.
// className ajoute la mise en page propre à la page (colonne, espacements)
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
