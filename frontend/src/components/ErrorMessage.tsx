import type { ReactNode } from 'react';

import { cn } from 'cn';

interface ErrorMessageProps {
  children: ReactNode;
  className?: string;
}

export function ErrorMessage({ children, className }: ErrorMessageProps) {
  return (
    <p
      role="alert"
      className={cn('rounded-lg bg-destructive/10 px-3 py-2 text-destructive', className)}
    >
      {children}
    </p>
  );
}
