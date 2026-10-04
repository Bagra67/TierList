import type { ReactNode } from 'react';

import { cn } from '@/lib/utils';

interface ErrorMessageProps {
  children: ReactNode;
  className?: string;
}

// Message d'erreur affiché à l'utilisateur, annoncé tout de suite par les lecteurs d'écran
export function ErrorMessage({ children, className }: ErrorMessageProps) {
  return (
    <p role="alert" className={cn('text-destructive', className)}>
      {children}
    </p>
  );
}
